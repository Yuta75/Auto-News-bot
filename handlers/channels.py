"""
/add_chnl  /rem_chnl  /view_chnl — channel management
"""

import logging

from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.types import Message

from utils.auth import admin_only

logger = logging.getLogger(__name__)


def _parse_arg(arg: str):
    """Return int ID or @username string."""
    arg = arg.strip()
    if arg.lstrip("-").isdigit():
        return int(arg)
    return arg if arg.startswith("@") else f"@{arg}"


@Client.on_message(filters.command("add_chnl"))
@admin_only
async def cmd_add_chnl(client: Client, msg: Message):
    db  = client.db
    cfg = client.cfg

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply(
            "⚠️ **Usage:** `/add_chnl <@username or channel_id>`\n\n"
            "Make sure the bot is an **admin** in the channel first."
        )
        return

    arg  = _parse_arg(parts[1])
    wait = await msg.reply("⏳ Verifying channel access…")

    try:
        chat = await client.get_chat(arg)
    except Exception as e:
        await wait.edit(
            f"❌ Cannot access channel: `{e}`\n\n"
            "Ensure the bot is an admin in that channel."
        )
        return

    if chat.type not in (ChatType.CHANNEL, ChatType.SUPERGROUP):
        await wait.edit("⚠️ Only channels and supergroups are supported.")
        return

    # Verify bot has admin rights
    try:
        me     = await client.get_me()
        member = await client.get_chat_member(chat.id, me.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            await wait.edit(
                "❌ Bot is **not an admin** in this channel.\n"
                "Please promote it first, then retry."
            )
            return
    except Exception:
        pass  # Some channels skip this check

    # Read live limit from DB settings
    max_ch = await db.get_setting("max_channels", cfg.MAX_CHANNELS)
    total  = await db.channel_count()
    if total >= max_ch:
        await wait.edit(f"⚠️ Channel limit reached `({total}/{max_ch})`. Remove one first or raise the limit via `/set_max_channels`.")
        return

    if await db.channel_exists(chat.id):
        await wait.edit("✦ This channel is **already registered**.")
        return

    username = f"@{chat.username}" if chat.username else None
    added    = await db.add_channel(chat.id, chat.title, username, msg.from_user.id)

    if added:
        await wait.edit(
            f"✅ **Channel added!**\n\n"
            f"**Title:** {chat.title}\n"
            f"**ID:** `{chat.id}`\n"
            f"**Username:** {username or '—'}"
        )
    else:
        await wait.edit("❌ Failed to add channel (already exists).")


@Client.on_message(filters.command("rem_chnl"))
@admin_only
async def cmd_rem_chnl(client: Client, msg: Message):
    db = client.db

    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.reply("⚠️ **Usage:** `/rem_chnl <@username or channel_id>`")
        return

    arg        = _parse_arg(parts[1])
    channel_id = None

    if isinstance(arg, int):
        channel_id = arg
    else:
        try:
            chat       = await client.get_chat(arg)
            channel_id = chat.id
        except Exception:
            for c in await db.get_all_channels():
                if c.get("username") == arg:
                    channel_id = c["channel_id"]
                    break

    if channel_id is None:
        await msg.reply("⚠️ Could not resolve channel. Try the numeric ID from `/view_chnl`.")
        return

    removed = await db.remove_channel(channel_id)
    if removed:
        await msg.reply(f"🗑 **Channel removed:** `{channel_id}`")
    else:
        await msg.reply("⚠️ Channel not found. Check `/view_chnl`.")


@Client.on_message(filters.command("view_chnl"))
@admin_only
async def cmd_view_chnl(client: Client, msg: Message):
    db       = client.db
    channels = await db.get_all_channels()

    if not channels:
        await msg.reply("📭 No channels added yet.\nUse `/add_chnl` to add one.")
        return

    lines = [f"✦ **Publish Channels** `({len(channels)})`\n"]
    for i, c in enumerate(channels, 1):
        title    = c.get("title", "Unknown")
        cid      = c["channel_id"]
        username = c.get("username") or "—"
        lines.append(f"**{i}.** {title}\n    ID: `{cid}` · {username}\n")

    await msg.reply("\n".join(lines))
