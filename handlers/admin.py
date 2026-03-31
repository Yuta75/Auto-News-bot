"""
/force_poll — immediately run one RSS poll cycle.
Reuses the shared RSSPoller instance attached to the client,
so feed error state and live settings are preserved.
Admin only.
"""

import logging

from pyrogram import Client, filters
from pyrogram.types import Message

from utils.auth import admin_only

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("force_poll"))
@admin_only
async def cmd_force_poll(client: Client, msg: Message):
    db = client.db

    if await db.rss_count() == 0:
        await msg.reply("⚠️ No RSS feeds added. Use `/add_rss` first.")
        return
    if await db.channel_count() == 0:
        await msg.reply("⚠️ No channels added. Use `/add_chnl` first.")
        return

    wait = await msg.reply("⏳ Fetching latest news…")
    try:
        # Reuse the running poller instance — shares feed error state + live settings
        await client.poller.poll_once()
        await wait.edit("✅ Poll complete! New articles (if any) have been published.")
    except Exception as e:
        logger.error(f"Force poll error: {e}", exc_info=True)
        await wait.edit(f"❌ Poll failed:\n`{e}`")
