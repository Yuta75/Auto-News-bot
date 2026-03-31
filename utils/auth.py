"""
Auth decorators — admin_only and owner_only.

admin_only  : allows owner + extra admins
owner_only  : allows ONLY the owner (Admins[0])
"""

import functools
from pyrogram.types import Message


def admin_only(func):
    """Allow owner and all admins. Silently blocks others."""
    @functools.wraps(func)
    async def wrapper(client, msg: Message, *args, **kwargs):
        if not msg.from_user:
            return
        if not client.cfg.is_admin(msg.from_user.id):
            await msg.reply("🚫 **Access denied.** Admin only.")
            return
        return await func(client, msg, *args, **kwargs)
    return wrapper


def owner_only(func):
    """Allow ONLY the owner (Admins[0]). Used for destructive/sensitive ops."""
    @functools.wraps(func)
    async def wrapper(client, msg: Message, *args, **kwargs):
        if not msg.from_user:
            return
        if not client.cfg.is_owner(msg.from_user.id):
            await msg.reply("🚫 **Owner only.** This action is restricted to the bot owner.")
            return
        return await func(client, msg, *args, **kwargs)
    return wrapper
