"""
/status — bot health, uptime, DB & publish stats
"""

import platform
import time

from pyrogram import Client, filters
from pyrogram.types import Message

from utils.auth import admin_only
from utils.formatting import fmt_dt, fmt_uptime

_start_time = time.time()


@Client.on_message(filters.command("status"))
@admin_only
async def cmd_status(client: Client, msg: Message):
    db  = client.db
    cfg = client.cfg

    db_ok     = await db.ping()
    rss_count = await db.rss_count()
    ch_count  = await db.channel_count()
    stats     = await db.get_stats()
    interval  = await db.get_setting("poll_interval", cfg.POLL_INTERVAL)

    db_icon  = "🟢" if db_ok else "🔴"
    db_label = "Connected" if db_ok else "Disconnected ⚠️"
    uptime   = fmt_uptime(int(time.time() - _start_time))

    text = (
        f"✦ **Bot Status**\n\n"
        f"⏱ **Uptime:** `{uptime}`\n"
        f"{db_icon} **Database:** {db_label}\n"
        f"📡 **RSS Feeds:** `{rss_count}`\n"
        f"📢 **Channels:** `{ch_count}`\n"
        f"🔄 **Poll Interval:** `{interval}s`\n\n"
        f"📨 **Articles Published:** `{stats['published']}`\n"
        f"🕐 **Last Published:** `{fmt_dt(stats.get('last_published'))}`\n\n"
        f"👑 **Owner:** `{cfg.ADMINS[0]}`\n"
        f"🛡 **Admins:** `{len(cfg.ADMINS)}`\n\n"
        f"🐍 Python `{platform.python_version()}` · PyroFork"
    )
    await msg.reply(text)
