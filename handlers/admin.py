"""
/force_poll — immediately run one RSS poll cycle
Admin only
"""

import logging

from pyrogram import Client, filters
from pyrogram.types import Message

from services.rss_poller import RSSPoller
from utils.auth import admin_only

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("force_poll"))
@admin_only
async def cmd_force_poll(client: Client, msg: Message):
    db  = client.db
    cfg = client.cfg

    if await db.rss_count() == 0:
        await msg.reply("⚠️ No RSS feeds added. Use `/add_rss` first.")
        return
    if await db.channel_count() == 0:
        await msg.reply("⚠️ No channels added. Use `/add_chnl` first.")
        return

    wait   = await msg.reply("⏳ Fetching latest news…")
    poller = RSSPoller(client, db, cfg)

    try:
        await poller._poll_all()
        await wait.edit("✅ Poll complete! New articles (if any) have been published.")
    except Exception as e:
        logger.error(f"Force poll error: {e}", exc_info=True)
        await wait.edit(f"❌ Poll failed:\n`{e}`")
