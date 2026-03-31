"""
/add_rss  /rem_rss  /view_rss — RSS feed management
"""

import logging

import aiohttp
import feedparser
from pyrogram import Client, filters
from pyrogram.types import Message

from utils.auth import admin_only

logger = logging.getLogger(__name__)


async def _validate_feed(url: str) -> tuple[bool, str]:
    """Fetch and validate an RSS/Atom URL. Returns (ok, feed_title_or_error)."""
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "AnimeNewsBot/2.0"},
        ) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False, f"HTTP {resp.status}"
                content = await resp.read()

        parsed = feedparser.parse(content)
        if not parsed.get("entries"):
            return False, "No entries found — not a valid RSS/Atom feed."
        title = parsed.feed.get("title", url)
        return True, title
    except Exception as e:
        return False, str(e)


@Client.on_message(filters.command("add_rss"))
@admin_only
async def cmd_add_rss(client: Client, msg: Message):
    db  = client.db
    cfg = client.cfg

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 2:
        await msg.reply(
            "⚠️ **Usage:** `/add_rss <feed_url> [optional name]`\n\n"
            "**Example:**\n`/add_rss https://www.crunchyroll.com/newsrss Crunchyroll`"
        )
        return

    url = parts[1].strip()
    custom_name = parts[2].strip() if len(parts) == 3 else None

    if not url.startswith(("http://", "https://")):
        await msg.reply("⚠️ URL must start with `http://` or `https://`")
        return

    if await db.rss_exists(url):
        await msg.reply("✦ This feed is **already added**.")
        return

    # Read live limit from DB settings
    max_rss = await db.get_setting("max_rss", cfg.MAX_RSS)
    total   = await db.rss_count()
    if total >= max_rss:
        await msg.reply(f"⚠️ RSS limit reached `({total}/{max_rss})`. Remove one first or raise the limit via `/set_max_rss`.")
        return

    wait  = await msg.reply("⏳ Validating feed…")
    valid, info = await _validate_feed(url)

    if not valid:
        await wait.edit(f"❌ **Invalid feed.**\n`{info}`")
        return

    name  = custom_name or info
    added = await db.add_rss(url, name, msg.from_user.id)

    if added:
        await wait.edit(
            f"✅ **RSS feed added!**\n\n"
            f"**Name:** {name}\n"
            f"**URL:** `{url}`"
        )
    else:
        await wait.edit("❌ Failed to add (already exists).")


@Client.on_message(filters.command("rem_rss"))
@admin_only
async def cmd_rem_rss(client: Client, msg: Message):
    db = client.db

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("⚠️ **Usage:** `/rem_rss <feed_url>`")
        return

    url     = parts[1].strip()
    removed = await db.remove_rss(url)

    if removed:
        await msg.reply(f"🗑 **Feed removed:**\n`{url}`")
    else:
        await msg.reply("⚠️ Feed not found. Check `/view_rss` for the exact URL.")


@Client.on_message(filters.command("view_rss"))
@admin_only
async def cmd_view_rss(client: Client, msg: Message):
    db    = client.db
    feeds = await db.get_all_rss()

    if not feeds:
        await msg.reply("📭 No RSS feeds added yet.\nUse `/add_rss` to add one.")
        return

    lines = [f"✦ **Active RSS Feeds** `({len(feeds)})`\n"]
    for i, f in enumerate(feeds, 1):
        name   = f.get("name", f["url"])
        url    = f["url"]
        active = "🟢" if f.get("active", True) else "🔴"
        lines.append(f"**{i}.** {active} {name}\n    `{url}`\n")

    await msg.reply("\n".join(lines))
