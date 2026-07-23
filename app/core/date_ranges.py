from datetime import date, timedelta

from fastapi import HTTPException

from app.core.timezone import today_pkt

VALID_RANGES = {"weekly", "biweekly", "monthly", "custom"}


def resolve_range(
    range_: str,
    start_date: date | None,
    end_date: date | None,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    """Turn a range keyword (+ optional custom bounds) into an inclusive (start, end) pair."""
    today = today or today_pkt()
    if range_ not in VALID_RANGES:
        raise HTTPException(status_code=422, detail=f"Invalid range: {range_}")
    if range_ == "weekly":
        return today - timedelta(days=7), today
    if range_ == "biweekly":
        return today - timedelta(days=14), today
    if range_ == "monthly":
        return today - timedelta(days=30), today
    # custom
    if not start_date or not end_date:
        raise HTTPException(
            status_code=422, detail="start_date and end_date are required for range=custom"
        )
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    return start_date, end_date
