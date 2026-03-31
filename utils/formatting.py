"""
Shared formatting helpers used across handlers and services.
"""

from datetime import datetime


def fmt_dt(dt) -> str:
    """Format a datetime object to a readable string."""
    if not dt:
        return "Never"
    if hasattr(dt, "strftime"):
        return dt.strftime("%d %b %Y · %H:%M UTC")
    return str(dt)


def fmt_uptime(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m {s}s"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


def truncate(text: str, max_len: int = 300) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"
