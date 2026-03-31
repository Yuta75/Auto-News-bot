"""
config.py
---------
Central configuration class that loads everything from environment variables.
"""

import os
import sys
import logging
from typing import List

logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        # ── REQUIRED SETTINGS ───────────────────────────────────────────────
        self.BOT_TOKEN: str = _require("BOT_TOKEN")
        self.API_ID: int    = int(_require("API_ID"))
        self.API_HASH: str  = _require("API_HASH")
        self.MONGO_URI: str = _require("MONGO_URI")

        owner_id = int(_require("OWNER_ID"))

        # ── OPTIONAL SETTINGS ───────────────────────────────────────────────
        self.DB_NAME: str        = os.getenv("DB_NAME", "anime_news_bot")
        self.POLL_INTERVAL: int  = int(os.getenv("POLL_INTERVAL", "300"))
        self.MAX_RSS: int        = int(os.getenv("MAX_RSS", "25"))
        self.MAX_CHANNELS: int   = int(os.getenv("MAX_CHANNELS", "10"))

        # ── WEBHOOK SETTINGS ────────────────────────────────────────────────
        self.WEBHOOK: bool = os.getenv("WEBHOOK", "false").lower() == "true"

        # ── POST FORMATTING ─────────────────────────────────────────────────
        self.DISABLE_WEB_PREVIEW: bool = os.getenv("DISABLE_WEB_PREVIEW", "false").lower() == "true"
        self.POST_FOOTER: str          = os.getenv("POST_FOOTER", "")

        # ── ADMINS ──────────────────────────────────────────────────────────
        extra = _parse_ids(os.getenv("ADMINS", ""))
        self.ADMINS: List[int] = [owner_id] + [uid for uid in extra if uid != owner_id]

        logger.info(f"✅ Config loaded | Owner: {self.ADMINS[0]} | Webhook Mode: {self.WEBHOOK}")

    # Permission helpers
    def is_owner(self, user_id: int) -> bool:
        return user_id == self.ADMINS[0]

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.ADMINS

    def add_admin(self, user_id: int) -> bool:
        if user_id not in self.ADMINS:
            self.ADMINS.append(user_id)
            return True
        return False

    def remove_admin(self, user_id: int) -> bool:
        if user_id == self.ADMINS[0]:
            return False
        if user_id in self.ADMINS:
            self.ADMINS.remove(user_id)
            return True
        return False

    # Live update methods
    def update_poll_interval(self, seconds: int):
        self.POLL_INTERVAL = max(30, seconds)

    def update_max_rss(self, n: int):
        self.MAX_RSS = max(1, n)

    def update_max_channels(self, n: int):
        self.MAX_CHANNELS = max(1, n)

    def set_post_footer(self, text: str):
        self.POST_FOOTER = text.strip()


# ── Internal helpers ────────────────────────────────────────────────────────
def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        logger.critical(f"❌ Required env var '{key}' is not set. Exiting.")
        sys.exit(1)
    return val


def _parse_ids(raw: str) -> List[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
