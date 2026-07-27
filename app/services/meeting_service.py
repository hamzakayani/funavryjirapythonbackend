from datetime import datetime
from typing import Optional

from dateutil.rrule import rrulestr
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Meeting, MeetingAttendee, User
from app.repositories import MeetingAttendeeRepository, MeetingRepository, UserRepository
from app.schemas import AttendeeOut, MeetingCreateRequest, MeetingOut, MeetingUpdateRequest

MAX_RECURRENCE_EXPANSION = 500  # hard cap on generated occurrences per meeting per query


class MeetingService:
    def __init__(self, db: Session):
        self.db = db
        self.meetings = MeetingRepository(db)
        self.attendees = MeetingAttendeeRepository(db)
        self.users = UserRepository(db)

    # -- conversion ------------------------------------------------------

    def _attendee_out(self, attendee: MeetingAttendee) -> AttendeeOut:
        user = self.users.get_by_id(attendee.user_id) if attendee.user_id else None
        return AttendeeOut(
            id=attendee.id,
            user_id=attendee.user_id,
            email=attendee.email,
            name=user.name if user else None,
            avatar_url=user.avatar_url if user else None,
            response_status=attendee.response_status.value,
            is_organizer=attendee.is_organizer,
        )

    def _meeting_to_out(self, meeting: Meeting, occurrence_start: Optional[datetime] = None) -> MeetingOut:
        duration = meeting.end_at - meeting.start_at
        start_at = occurrence_start or meeting.start_at
        end_at = start_at + duration
        return MeetingOut(
            id=meeting.id,
            owner_id=meeting.owner_id,
            title=meeting.title,
            description=meeting.description,
            location=meeting.location,
            start_at=start_at,
            end_at=end_at,
            all_day=meeting.all_day,
            timezone=meeting.timezone,
            rrule=meeting.rrule,
            meet_link=meeting.meet_link,
            meet_link_type=meeting.meet_link_type,
            project_id=meeting.project_id,
            issue_id=meeting.issue_id,
            source=meeting.source.value,
            google_event_id=meeting.google_event_id,
            google_html_link=meeting.google_html_link,
            status=meeting.status.value,
            attendees=[self._attendee_out(a) for a in meeting.attendees],
        )

    # -- authorization -----------------------------------------------------

    def _get_owned_meeting(self, meeting_id: int, user: User) -> Meeting:
        meeting = self.meetings.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        if meeting.owner_id != user.id:
            raise HTTPException(status_code=403, detail="Only the organizer can modify this meeting")
        return meeting

    def _resolve_attendees(self, attendee_inputs) -> list[dict]:
        """Each input is either {user_id} (platform user) or {email} (external).
        Returns a de-duplicated list of {user_id, email} dicts."""
        resolved: dict[str, dict] = {}
        for a in attendee_inputs:
            if a.user_id:
                user = self.users.get_by_id(a.user_id)
                if not user:
                    raise HTTPException(status_code=404, detail=f"User {a.user_id} not found")
                resolved[user.email.lower()] = {"user_id": user.id, "email": user.email}
            elif a.email:
                resolved.setdefault(a.email, {"user_id": None, "email": a.email})
        return list(resolved.values())

    # -- CRUD ----------------------------------------------------------------

    def create_meeting(self, data: MeetingCreateRequest, user: User) -> Meeting:
        if data.end_at <= data.start_at:
            raise HTTPException(status_code=422, detail="end_at must be after start_at")

        meet_link = None
        if data.meet_link_type == "manual":
            meet_link = data.manual_meet_link

        meeting = Meeting(
            owner_id=user.id,
            title=data.title.strip(),
            description=data.description,
            location=data.location,
            start_at=data.start_at,
            end_at=data.end_at,
            all_day=data.all_day,
            timezone=data.timezone,
            rrule=data.rrule,
            meet_link=meet_link,
            meet_link_type=data.meet_link_type,
            project_id=data.project_id,
            issue_id=data.issue_id,
        )
        self.meetings.create(meeting)

        self.attendees.create(
            MeetingAttendee(meeting_id=meeting.id, user_id=user.id, email=user.email, is_organizer=True)
        )
        for a in self._resolve_attendees(data.attendees):
            if a["email"].lower() == user.email.lower():
                continue
            self.attendees.create(MeetingAttendee(meeting_id=meeting.id, **a))

        self.meetings.save()
        self.meetings.refresh(meeting)
        return meeting

    def update_meeting(self, meeting_id: int, data: MeetingUpdateRequest, user: User) -> Meeting:
        meeting = self._get_owned_meeting(meeting_id, user)
        updates = data.model_dump(exclude_unset=True)

        for field in (
            "title", "description", "location", "start_at", "end_at",
            "all_day", "timezone", "rrule", "project_id", "issue_id",
        ):
            if field in updates:
                setattr(meeting, field, updates[field])

        if "meet_link_type" in updates:
            meeting.meet_link_type = updates["meet_link_type"]
            if updates["meet_link_type"] == "manual":
                meeting.meet_link = updates.get("manual_meet_link") or data.manual_meet_link
            elif updates["meet_link_type"] == "none":
                meeting.meet_link = None

        if meeting.meet_link_type == "manual" and "manual_meet_link" in updates and "meet_link_type" not in updates:
            meeting.meet_link = updates["manual_meet_link"]

        if meeting.end_at <= meeting.start_at:
            raise HTTPException(status_code=422, detail="end_at must be after start_at")

        if data.attendees is not None:
            self.attendees.delete_for_meeting(meeting.id)
            self.attendees.create(
                MeetingAttendee(meeting_id=meeting.id, user_id=user.id, email=user.email, is_organizer=True)
            )
            for a in self._resolve_attendees(data.attendees):
                if a["email"].lower() == user.email.lower():
                    continue
                self.attendees.create(MeetingAttendee(meeting_id=meeting.id, **a))

        self.meetings.save()
        self.meetings.refresh(meeting)
        return meeting

    def delete_meeting(self, meeting_id: int, user: User) -> Meeting:
        meeting = self._get_owned_meeting(meeting_id, user)
        self.meetings.delete(meeting)
        self.meetings.save()
        return meeting

    # -- listing with recurrence expansion ------------------------------------

    def list_meetings(self, user: User, start: datetime, end: datetime) -> list[MeetingOut]:
        raw_meetings = self.meetings.list_for_user_in_range(user.id, start, end)
        results: list[MeetingOut] = []
        for meeting in raw_meetings:
            if not meeting.rrule:
                results.append(self._meeting_to_out(meeting))
                continue
            try:
                rule = rrulestr(meeting.rrule, dtstart=meeting.start_at)
            except ValueError:
                results.append(self._meeting_to_out(meeting))
                continue
            occurrences = rule.between(start, end, inc=True)
            for occurrence_start in occurrences[:MAX_RECURRENCE_EXPANSION]:
                results.append(self._meeting_to_out(meeting, occurrence_start=occurrence_start))
        results.sort(key=lambda m: m.start_at)
        return results

    def get_meeting(self, meeting_id: int, user: User) -> Meeting:
        meeting = self.meetings.get_by_id(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        is_attendee = any(a.user_id == user.id for a in meeting.attendees)
        if meeting.owner_id != user.id and not is_attendee:
            raise HTTPException(status_code=403, detail="Not invited to this meeting")
        return meeting
