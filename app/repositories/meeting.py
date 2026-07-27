from datetime import datetime
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Meeting, MeetingAttendee, MeetingStatus


class MeetingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, meeting_id: int) -> Optional[Meeting]:
        return self.db.query(Meeting).filter(Meeting.id == meeting_id).first()

    def get_by_google_event_id(self, owner_id: int, google_event_id: str) -> Optional[Meeting]:
        return (
            self.db.query(Meeting)
            .filter(Meeting.owner_id == owner_id, Meeting.google_event_id == google_event_id)
            .first()
        )

    def list_for_user_in_range(self, user_id: int, start: datetime, end: datetime) -> list[Meeting]:
        """Meetings the user owns or is an invited attendee on, whose
        non-recurring window overlaps [start, end]. Recurring meetings
        (rrule set) are always included regardless of their own start_at,
        since the service layer expands their occurrences into the range."""
        owned_or_attending = (
            self.db.query(Meeting)
            .outerjoin(MeetingAttendee, MeetingAttendee.meeting_id == Meeting.id)
            .filter(
                Meeting.status == MeetingStatus.Confirmed,
                or_(Meeting.owner_id == user_id, MeetingAttendee.user_id == user_id),
            )
            .filter(
                or_(
                    Meeting.rrule.isnot(None),
                    and_start_end_overlap(Meeting, start, end),
                )
            )
            .distinct()
            .all()
        )
        return owned_or_attending

    def create(self, meeting: Meeting) -> Meeting:
        self.db.add(meeting)
        self.db.flush()
        return meeting

    def save(self) -> None:
        self.db.commit()

    def refresh(self, meeting: Meeting) -> Meeting:
        self.db.refresh(meeting)
        return meeting

    def delete(self, meeting: Meeting) -> None:
        self.db.delete(meeting)


def and_start_end_overlap(Meeting, start: datetime, end: datetime):
    return (Meeting.start_at <= end) & (Meeting.end_at >= start)


class MeetingAttendeeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, attendee: MeetingAttendee) -> MeetingAttendee:
        self.db.add(attendee)
        self.db.flush()
        return attendee

    def list_for_meeting(self, meeting_id: int) -> list[MeetingAttendee]:
        return self.db.query(MeetingAttendee).filter(MeetingAttendee.meeting_id == meeting_id).all()

    def delete_for_meeting(self, meeting_id: int) -> None:
        self.db.query(MeetingAttendee).filter(MeetingAttendee.meeting_id == meeting_id).delete()

    def save(self) -> None:
        self.db.commit()
