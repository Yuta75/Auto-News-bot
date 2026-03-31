"""
/start and /help — public entry points
"""

from pyrogram import Client, filters
from pyrogram.types import Message

START_TEXT = """
✦ **Anime News Bot**

_Automatically fetch & publish anime news to your Telegram channels via RSS feeds._

**◎ Features**
• Fully dynamic — manage everything via commands
• Multi-channel auto-publishing
• Auto-dedup — never reposts the same article
• Default Crunchyroll & ANN feeds pre-loaded
• Admin panel with live settings control
• Lightweight — runs on Render, Koyeb, Heroku, VPS

Use /help to see all available commands.
"""

HELP_TEXT = """
✦ **Command Reference**

**‹ RSS Management ›** _(Admin)_
`/add_rss <url> [name]` — Add an RSS feed
`/rem_rss <url>` — Remove a feed
`/view_rss` — List all active feeds

**‹ Channel Management ›** _(Admin)_
`/add_chnl <@username or id>` — Add a publish channel
`/rem_chnl <@username or id>` — Remove a channel
`/view_chnl` — List all channels

**‹ Tools ›** _(Admin)_
`/force_poll` — Manually trigger a news fetch
`/status` — Bot health & stats

**‹ Admin Panel ›** _(Owner)_
`/settings` — View all current settings
`/set_interval <seconds>` — Change poll interval
`/set_max_rss <n>` — Change RSS feed limit
`/set_max_channels <n>` — Change channel limit
`/toggle_preview` — Toggle web preview on/off
`/set_footer <text>` — Set post footer text
`/clear_footer` — Remove post footer
`/add_admin <user_id>` — Add an admin
`/rem_admin <user_id>` — Remove an admin
`/list_admins` — List all admins
`/clear_seen` — Clear dedup cache (re-publish allowed)
`/reset_stats` — Reset publish stats

> ⚠️ Make sure the bot is an **admin** in any channel you add.
"""


@Client.on_message(filters.command("start") & filters.private)
async def cmd_start(client: Client, msg: Message):
    await msg.reply(START_TEXT)


@Client.on_message(filters.command("help"))
async def cmd_help(client: Client, msg: Message):
    await msg.reply(HELP_TEXT)
