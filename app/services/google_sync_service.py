from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as date_parser
from sqlalchemy.orm import Session

from app.models import GoogleAccount, Meeting, MeetingAttendee, MeetingSource, MeetingStatus
from app.repositories import GoogleAccountRepository, MeetingAttendeeRepository, MeetingRepository, UserRepository
from app.services.google_calendar_client import GoogleCalendarClient, GoogleSyncTokenExpired


class GoogleSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.meetings = MeetingRepository(db)
        self.attendees = MeetingAttendeeRepository(db)
        self.google_accounts = GoogleAccountRepository(db)
        self.users = UserRepository(db)

    def _parse_event_time(self, time_obj: dict) -> Optional[datetime]:
        raw = time_obj.get("dateTime") or time_obj.get("date")
        if not raw:
            return None
        parsed = date_parser.isoparse(raw)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.replace(tzinfo=None)  # store naive UTC-equivalent, matching existing convention

    def _upsert_event(self, account: GoogleAccount, event: dict) -> None:
        google_event_id = event["id"]
        if event.get("status") == "cancelled":
            existing = self.meetings.get_by_google_event_id(account.user_id, google_event_id)
            if existing:
                self.meetings.delete(existing)
            return

        start = self._parse_event_time(event.get("start", {}))
        end = self._parse_event_time(event.get("end", {}))
        if not start or not end:
            return

        meeting = self.meetings.get_by_google_event_id(account.user_id, google_event_id)
        is_new = meeting is None
        if is_new:
            # If this same Google event is already represented locally as a
            # meeting owned by someone else with this account's user listed as
            # an attendee, the user already sees it via that owner's meeting +
            # their attendee row. Creating our own pulled copy here would show
            # the event twice, so skip it. This ONLY gates the create-new-row
            # path — an existing pulled copy (is_new False) is left untouched.
            if self.meetings.exists_as_attendee_elsewhere(account.user_id, google_event_id):
                return
            meeting = Meeting(
                owner_id=account.user_id,
                source=MeetingSource.Google,
                google_event_id=google_event_id,
                google_calendar_id=account.calendar_id,
            )

        meeting.title = event.get("summary", "(No title)")
        meeting.description = event.get("description")
        meeting.location = event.get("location")
        meeting.start_at = start
        meeting.end_at = end
        meeting.all_day = "date" in event.get("start", {})
        meeting.timezone = event.get("start", {}).get("timeZone", "UTC")
        recurrence = event.get("recurrence") or []
        rrule_line = next((r for r in recurrence if r.startswith("RRULE:")), None)
        meeting.rrule = rrule_line.replace("RRULE:", "") if rrule_line else None
        meeting.meet_link = event.get("hangoutLink")
        meeting.meet_link_type = "google_meet" if event.get("hangoutLink") else "none"
        meeting.google_etag = event.get("etag")
        meeting.google_html_link = event.get("htmlLink")
        meeting.status = MeetingStatus.Confirmed
        meeting.last_synced_at = datetime.utcnow()

        if is_new:
            self.meetings.create(meeting)
        self.meetings.save()

        self.attendees.delete_for_meeting(meeting.id)
        for g_attendee in event.get("attendees", []):
            email = g_attendee.get("email")
            if not email:
                continue
            user = self.users.get_by_email(email)
            self.attendees.create(
                MeetingAttendee(
                    meeting_id=meeting.id,
                    user_id=user.id if user else None,
                    email=email,
                    is_organizer=g_attendee.get("organizer", False),
                )
            )
        self.attendees.save()

    def pull_sync_for_account(self, account: GoogleAccount) -> int:
        client = GoogleCalendarClient(account, self.db)
        try:
            events, next_sync_token = client.list_events_incremental(account.sync_token)
        except GoogleSyncTokenExpired:
            account.sync_token = None
            self.google_accounts.save()
            events, next_sync_token = client.list_events_incremental(None)

        for event in events:
            self._upsert_event(account, event)

        account.sync_token = next_sync_token
        account.last_synced_at = datetime.utcnow()
        self.google_accounts.save()
        return len(events)
