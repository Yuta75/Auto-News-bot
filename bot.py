"""
Anime News Bot — Production Edition
Lightweight, production-ready for Render / Koyeb / Heroku / VPS

Webhook mode  : set WEBHOOK=true in env — spins an aiohttp health-check server
                so platforms like Render/Koyeb don't kill the container.
Polling mode  : set WEBHOOK=false (default) — standard long polling.

On startup:
 - Syncs persistent DB settings (extra admins, poll interval, limits) back into
   the live Config object so runtime config always matches what was last saved.
"""

import asyncio
import logging
import os

# Load .env file automatically if present (local dev / VPS)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from aiohttp import web
from pyrogram import Client, idle

from config import Config
from database import CosmicBotz
from services.rss_poller import RSSPoller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Health-check webhook server ───────────────────────────────────────────────

async def _health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def _start_webhook(host: str, port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"🌐 Health-check server running on {host}:{port}")
    return runner


# ── Settings sync: DB → Config ────────────────────────────────────────────────

async def _sync_settings(db: CosmicBotz, cfg: Config):
    """
    On startup, read persisted settings from DB and apply them to the live
    Config object. This ensures settings changed via /set_* commands survive
    bot restarts.
    """
    s = await db.get_settings()

    cfg.POLL_INTERVAL       = s.get("poll_interval", cfg.POLL_INTERVAL)
    cfg.MAX_RSS             = s.get("max_rss", cfg.MAX_RSS)
    cfg.MAX_CHANNELS        = s.get("max_channels", cfg.MAX_CHANNELS)
    cfg.DISABLE_WEB_PREVIEW = s.get("disable_web_preview", False)
    cfg.POST_FOOTER         = s.get("post_footer", "")

    # Merge persisted extra admins into the live ADMINS list
    db_extra = s.get("extra_admins", [])
    for uid in db_extra:
        cfg.add_admin(uid)

    logger.info(
        f"⚙️  Settings synced from DB — "
        f"interval={cfg.POLL_INTERVAL}s, "
        f"max_rss={cfg.MAX_RSS}, "
        f"max_channels={cfg.MAX_CHANNELS}, "
        f"admins={cfg.ADMINS}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    cfg = Config()

    # Init DB
    db = CosmicBotz(cfg.MONGO_URI, cfg.DB_NAME)
    await db.init()

    # Seed default RSS feeds if none exist
    await db.seed_defaults()

    # Sync persisted settings back into live Config
    await _sync_settings(db, cfg)

    # PyroFork client — handlers auto-discovered from handlers/ via plugins
    app = Client(
        name="AnimeNewsBot",
        bot_token=cfg.BOT_TOKEN,
        api_id=cfg.API_ID,
        api_hash=cfg.API_HASH,
        plugins={"root": "handlers"},
    )

    # Attach shared objects — accessible in every handler via client.db / client.cfg
    app.db  = db
    app.cfg = cfg

    poller = RSSPoller(app, db, cfg)

    await app.start()
    logger.info(f"✅ Bot started. Owner: {cfg.ADMINS[0]} | Admins: {cfg.ADMINS}")

    # Launch background poller
    poller_task = asyncio.create_task(poller.run())

    if cfg.WEBHOOK:
        logger.info("🚀 Running in WEBHOOK / health-check mode")
        runner = await _start_webhook(cfg.WEBHOOK_HOST, cfg.WEBHOOK_PORT)
        await idle()
        poller.stop()
        await runner.cleanup()
    else:
        logger.info("🚀 Running in POLLING mode")
        await idle()
        poller.stop()

    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
