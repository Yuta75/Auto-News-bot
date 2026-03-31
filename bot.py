"""
bot.py (Main Entry Point)
-------------------------
Starts the Telegram bot, connects to MongoDB, and launches the RSS Poller.
Webhook host is hardcoded and port is taken directly from $PORT env var.
"""

import asyncio
import logging
import os

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


async def _health(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def _start_webhook(port: int) -> web.AppRunner:
    """Webhook server with hardcoded host 0.0.0.0"""
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logger.info(f"🌐 Health-check webhook server running on 0.0.0.0:{port}")
    return runner


async def _sync_settings(db: CosmicBotz, cfg: Config):
    s = await db.get_settings()
    cfg.POLL_INTERVAL       = s.get("poll_interval", cfg.POLL_INTERVAL)
    cfg.MAX_RSS             = s.get("max_rss", cfg.MAX_RSS)
    cfg.MAX_CHANNELS        = s.get("max_channels", cfg.MAX_CHANNELS)
    cfg.DISABLE_WEB_PREVIEW = s.get("disable_web_preview", False)
    cfg.POST_FOOTER         = s.get("post_footer", "")

    for uid in s.get("extra_admins", []):
        cfg.add_admin(uid)

    logger.info(f"⚙️ Settings synced | Interval: {cfg.POLL_INTERVAL}s")


async def main():
    cfg = Config()

    db = CosmicBotz(cfg.MONGO_URI, cfg.DB_NAME)
    await db.init()
    await db.seed_defaults()
    await _sync_settings(db, cfg)

    app = Client(
        name="AnimeDubBot",
        bot_token=cfg.BOT_TOKEN,
        api_id=cfg.API_ID,
        api_hash=cfg.API_HASH,
        plugins={"root": "handlers"},
    )

    app.db = db
    app.cfg = cfg

    poller = RSSPoller(app, db, cfg)
    app.poller = poller

    await app.start()
    logger.info(f"✅ Bot started successfully! Owner: {cfg.ADMINS[0]}")

    poller.start()

    if cfg.WEBHOOK:
        # PORT is taken directly from environment variable (Render.com standard)
        port = int(os.getenv("PORT"))
        logger.info("🚀 Starting in WEBHOOK mode")
        runner = await _start_webhook(port)
        await idle()
        poller.stop()
        await runner.cleanup()
    else:
        logger.info("🚀 Starting in POLLING mode")
        await idle()
        poller.stop()

    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
