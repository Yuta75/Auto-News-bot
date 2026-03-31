"""
services/rss_poller.py
----------------------
Background task that polls RSS feeds, filters dubs, extracts images,
and sends posts in the clean format you requested.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import aiohttp
import feedparser

from config import Config
from database import CosmicBotz

logger = logging.getLogger(__name__)

# ========================== DUB FILTER ==========================
ALLOWED_DUBS = ["Hindi", "English", "Russian"]

DUB_PATTERN = re.compile(
    r'\(\s*(' + '|'.join(ALLOWED_DUBS) + r')\s*Dub\s*\)',
    re.IGNORECASE
)

EMOJI_MAP = {
    "anime":   "🎌",
    "manga":   "📖",
    "review":  "⭐",
    "trailer": "🎥",
    "episode": "📺",
    "release": "🗓",
    "game":    "🎮",
    "movie":   "🎬",
    "news":    "📰",
}


def _pick_emoji(tags: List[str], title: str) -> str:
    blob = " ".join(tags + [title]).lower()
    for kw, em in EMOJI_MAP.items():
        if kw in blob:
            return em
    return "📰"


def _clean_html(raw: str, max_len: int = 300) -> str:
    text = re.sub(r"<[^>]+>", "", raw).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def _fmt_date(parsed) -> Optional[str]:
    if not parsed:
        return None
    try:
        dt = datetime(*parsed[:6], tzinfo=timezone.utc)
        return dt.strftime("%d %b %Y · %H:%M UTC")
    except Exception:
        return None


def _guid(entry: Dict, feed_url: str) -> str:
    raw = entry.get("id") or entry.get("link") or entry.get("title") or ""
    return hashlib.sha1(f"{feed_url}:{raw}".encode()).hexdigest()


def _is_desired_dub(entry: Dict) -> bool:
    title = entry.get("title", "") or ""
    summary = entry.get("summary", "") or entry.get("description", "")
    return bool(DUB_PATTERN.search(title) or DUB_PATTERN.search(summary))


def _extract_image(entry: Dict) -> Optional[str]:
    candidates = []
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image/"):
            candidates.append(enc.get("href") or enc.get("url"))
    for media in entry.get("media_content", []):
        candidates.append(media.get("url"))
    for thumb in entry.get("media_thumbnail", []):
        candidates.append(thumb.get("url"))
    for key in ["image", "thumbnail", "poster", "itunes_image"]:
        val = entry.get(key)
        if isinstance(val, dict):
            candidates.append(val.get("href") or val.get("url"))
        elif isinstance(val, str) and val.startswith("http"):
            candidates.append(val)

    for url in candidates:
        if url and url.startswith("http"):
            return url
    return None


def _format(entry: Dict, feed_name: str, footer: str = "") -> Tuple[str, Optional[str]]:
    title   = entry.get("title", "No Title").strip()
    link    = entry.get("link", "")
    summary = _clean_html(entry.get("summary", ""))
    tags    = [t.get("term", "") for t in entry.get("tags", [])]
    emoji   = _pick_emoji(tags, title)
    date    = _fmt_date(entry.get("published_parsed"))
    image   = _extract_image(entry)

    parts = [
        f"{emoji} **{title}**",
        "",
    ]
    if summary:
        parts.append(f"{summary}")
        parts.append("")
    if date:
        parts.append(f"🕐 {date}")
    parts.append(f"📡 {feed_name}")
    if link:
        parts.append(f"🔗 [Read more]({link})")
    if footer:
        parts.append(f"\n{footer}")

    caption = "\n".join(parts)
    return caption, image


class RSSPoller:
    def __init__(self, client, db: CosmicBotz, cfg: Config):
        self._client = client
        self._db     = db
        self._cfg    = cfg
        self._task: Optional[asyncio.Task] = None
        self._feed_errors: Dict[str, int]  = {}

    def start(self):
        self._task = asyncio.create_task(self._run())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()

    async def _run(self):
        interval = await self._db.get_setting("poll_interval", self._cfg.POLL_INTERVAL)
        logger.info(f"📡 RSS Poller started — interval {interval}s | Allowed Dubs: {ALLOWED_DUBS}")

        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                logger.info("📡 RSS Poller stopped.")
                break
            except Exception as e:
                logger.error(f"Poller loop error: {e}", exc_info=True)

            interval = await self._db.get_setting("poll_interval", self._cfg.POLL_INTERVAL)
            await asyncio.sleep(interval)

    async def poll_once(self):
        feeds    = await self._db.get_active_rss()
        channels = await self._db.get_all_channels()

        if not feeds or not channels:
            return

        channel_ids     = [c["channel_id"] for c in channels]
        disable_preview = await self._db.get_setting("disable_web_preview", False)
        footer          = await self._db.get_setting("post_footer", "")

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),
            headers={
                "User-Agent": "AnimeDubBot/2.1 (+https://t.me/yourbot)",
                "Accept": "application/rss+xml, text/xml, */*"
            },
        ) as session:
            for feed in feeds:
                await self._process_feed(feed, channel_ids, session, disable_preview, footer)

    async def _process_feed(
        self,
        feed: Dict,
        channel_ids: List[int],
        session: aiohttp.ClientSession,
        disable_preview: bool,
        footer: str,
    ):
        url = feed["url"]
        name = feed.get("name", url)

        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    self._log_feed_error(url, f"HTTP {resp.status}")
                    return
                content = await resp.read()
            self._feed_errors[url] = 0
        except Exception as e:
            self._log_feed_error(url, str(e))
            return

        try:
            entries = feedparser.parse(content).get("entries", [])
        except Exception as e:
            self._log_feed_error(url, f"Parse error: {e}")
            return

        new = 0
        for entry in reversed(entries):
            guid = _guid(entry, url)
            if await self._db.is_seen(guid):
                continue

            if not _is_desired_dub(entry):
                continue

            caption, image_url = _format(entry, name, footer)
            published = False

            for ch_id in channel_ids:
                try:
                    if image_url:
                        await self._client.send_photo(
                            ch_id,
                            image_url,
                            caption=caption,
                            parse_mode="Markdown"
                        )
                    else:
                        await self._client.send_message(
                            ch_id,
                            caption,
                            disable_web_page_preview=disable_preview,
                            parse_mode="Markdown"
                        )
                    published = True
                except Exception as e:
                    logger.warning(f"Send to {ch_id} failed: {e}")

            await self._db.mark_seen(guid)
            if published:
                new += 1
            await asyncio.sleep(0.6)

        if new:
            await self._db.increment_published(new)
            logger.info(f"📨 {new} new dub post(s) from '{name}'")

    def _log_feed_error(self, url: str, reason: str):
        count = self._feed_errors.get(url, 0) + 1
        self._feed_errors[url] = count
        if count in (1, 3, 5, 10) or count % 15 == 0:
            logger.warning(f"Feed error [{url}] (×{count}): {reason}")
