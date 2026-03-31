"""
Config — loaded entirely from environment variables.
No credentials are hardcoded anywhere.

ADMINS list:  The first entry is always the OWNER (Admins[0]).
              EXTRA_ADMINS are appended after.
              All permissions use the ADMINS list.
"""

import os
import sys
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Config:
    # ── Required ─────────────────────────────────────────────────────────────
    BOT_TOKEN: str  = field(default_factory=lambda: _require("BOT_TOKEN"))
    API_ID: int     = field(default_factory=lambda: int(_require("API_ID")))
    API_HASH: str   = field(default_factory=lambda: _require("API_HASH"))
    MONGO_URI: str  = field(default_factory=lambda: _require("MONGO_URI"))
    OWNER_ID: int   = field(default_factory=lambda: int(_require("OWNER_ID")))

    # ── Optional ─────────────────────────────────────────────────────────────
    DB_NAME: str        = field(default_factory=lambda: os.getenv("DB_NAME", "anime_news_bot"))
    POLL_INTERVAL: int  = field(default_factory=lambda: int(os.getenv("POLL_INTERVAL", "300")))
    MAX_RSS: int        = field(default_factory=lambda: int(os.getenv("MAX_RSS", "25")))
    MAX_CHANNELS: int   = field(default_factory=lambda: int(os.getenv("MAX_CHANNELS", "10")))

    # Extra admins: comma-separated Telegram user IDs
    EXTRA_ADMINS: List[int] = field(
        default_factory=lambda: _parse_ids(os.getenv("EXTRA_ADMINS", ""))
    )

    # ── Webhook ───────────────────────────────────────────────────────────────
    WEBHOOK: bool     = field(default_factory=lambda: os.getenv("WEBHOOK", "false").lower() == "true")
    WEBHOOK_HOST: str = field(default_factory=lambda: os.getenv("WEBHOOK_HOST", "0.0.0.0"))
    WEBHOOK_PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "8080")))

    # ── Post format ───────────────────────────────────────────────────────────
    DISABLE_WEB_PREVIEW: bool = field(
        default_factory=lambda: os.getenv("DISABLE_WEB_PREVIEW", "false").lower() == "true"
    )
    POST_FOOTER: str = field(default_factory=lambda: os.getenv("POST_FOOTER", ""))

    def __post_init__(self):
        # Build the unified ADMINS list: owner is always Admins[0]
        admins = [self.OWNER_ID]
        for uid in self.EXTRA_ADMINS:
            if uid != self.OWNER_ID:
                admins.append(uid)
        self.ADMINS: List[int] = admins
        logger.info(f"✅ Config loaded. Owner: {self.OWNER_ID} | Admins: {self.ADMINS}")

    # ── Permission helpers ────────────────────────────────────────────────────

    def is_owner(self, user_id: int) -> bool:
        """True only for the bot owner (Admins[0])."""
        return user_id == self.ADMINS[0]

    def is_admin(self, user_id: int) -> bool:
        """True for owner and all extra admins."""
        return user_id in self.ADMINS

    def add_admin(self, user_id: int) -> bool:
        """Dynamically add an admin at runtime (not persisted across restarts)."""
        if user_id not in self.ADMINS:
            self.ADMINS.append(user_id)
            return True
        return False

    def remove_admin(self, user_id: int) -> bool:
        """Remove an admin. Owner (Admins[0]) can never be removed."""
        if user_id == self.ADMINS[0]:
            return False  # can't remove owner
        if user_id in self.ADMINS:
            self.ADMINS.remove(user_id)
            return True
        return False

    def update_poll_interval(self, seconds: int):
        self.POLL_INTERVAL = max(30, seconds)

    def update_max_rss(self, n: int):
        self.MAX_RSS = max(1, n)

    def update_max_channels(self, n: int):
        self.MAX_CHANNELS = max(1, n)

    def toggle_web_preview(self) -> bool:
        self.DISABLE_WEB_PREVIEW = not self.DISABLE_WEB_PREVIEW
        return self.DISABLE_WEB_PREVIEW

    def set_post_footer(self, text: str):
        self.POST_FOOTER = text.strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        logger.critical(f"❌ Required env var '{key}' is not set. Exiting.")
        sys.exit(1)
    return val


def _parse_ids(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
