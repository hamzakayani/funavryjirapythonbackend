from datetime import date, datetime
from zoneinfo import ZoneInfo

PKT = ZoneInfo("Asia/Karachi")
UTC = ZoneInfo("UTC")

# Standups completed at/after this hour, Pakistan time, count as "Late" rather than on-time.
STANDUP_LATE_CUTOFF_HOUR = 15


def now_pkt() -> datetime:
    """Current instant, expressed in Pakistan Standard Time."""
    return datetime.now(PKT)


def today_pkt() -> date:
    """Today's calendar date in Pakistan Standard Time — the app's single
    notion of "today" for standups, date ranges, and other day-boundary
    logic, regardless of where the server itself is hosted."""
    return now_pkt().date()


def to_pkt(dt: datetime) -> datetime:
    """Convert a datetime to Pakistan Standard Time. Naive datetimes (as
    produced by datetime.utcnow() throughout this codebase) are assumed UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(PKT)


def is_after_standup_cutoff(dt: datetime) -> bool:
    """True if dt, converted to PKT, falls at/after the standup late cutoff."""
    return to_pkt(dt).hour >= STANDUP_LATE_CUTOFF_HOUR
