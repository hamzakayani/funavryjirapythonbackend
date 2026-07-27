import uuid
from datetime import datetime, timezone as dt_timezone
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models import GoogleAccount, Meeting
from app.repositories import GoogleAccountRepository
from app.services.google_oauth_service import GoogleOAuthService


class GoogleSyncTokenExpired(Exception):
    """Raised when Google returns 410 Gone for an invalid/expired syncToken."""


class GoogleCalendarClient:
    def __init__(self, account: GoogleAccount, db):
        self.account = account
        self.db = db
        self.oauth_service = GoogleOAuthService()
        self._service = None

    def _get_service(self):
        if self._service is None:
            creds = self.oauth_service.credentials_from_account(self.account)
            self._service = build("calendar", "v3", credentials=creds)
            self.oauth_service.persist_credentials(self.account, creds)
            GoogleAccountRepository(self.db).save()
        return self._service

    def _event_body(self, meeting: Meeting) -> dict:
        body = {
            "summary": meeting.title,
            "description": meeting.description or "",
            "location": meeting.location or "",
            "start": {"dateTime": meeting.start_at.isoformat(), "timeZone": meeting.timezone},
            "end": {"dateTime": meeting.end_at.isoformat(), "timeZone": meeting.timezone},
            "attendees": [{"email": a.email} for a in meeting.attendees],
        }
        if meeting.rrule:
            body["recurrence"] = [f"RRULE:{meeting.rrule}"]
        if meeting.meet_link_type == "google_meet":
            body["conferenceData"] = {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        return body

    def insert_event(self, meeting: Meeting) -> dict:
        service = self._get_service()
        body = self._event_body(meeting)
        conference_version = 1 if meeting.meet_link_type == "google_meet" else 0
        return (
            service.events()
            .insert(
                calendarId=self.account.calendar_id,
                body=body,
                conferenceDataVersion=conference_version,
                sendUpdates="all",
            )
            .execute()
        )

    def update_event(self, meeting: Meeting) -> dict:
        service = self._get_service()
        body = self._event_body(meeting)
        conference_version = 1 if meeting.meet_link_type == "google_meet" else 0
        return (
            service.events()
            .update(
                calendarId=self.account.calendar_id,
                eventId=meeting.google_event_id,
                body=body,
                conferenceDataVersion=conference_version,
                sendUpdates="all",
            )
            .execute()
        )

    def delete_event(self, meeting: Meeting) -> None:
        service = self._get_service()
        try:
            service.events().delete(
                calendarId=self.account.calendar_id,
                eventId=meeting.google_event_id,
                sendUpdates="all",
            ).execute()
        except HttpError as e:
            if e.resp.status not in (404, 410):
                raise

    def list_events_incremental(self, sync_token: Optional[str] = None) -> tuple[list[dict], Optional[str]]:
        service = self._get_service()
        events: list[dict] = []
        page_token = None
        params: dict = {"calendarId": self.account.calendar_id, "singleEvents": True}
        if sync_token:
            params["syncToken"] = sync_token
        else:
            now = datetime.now(dt_timezone.utc)
            params["timeMin"] = now.replace(year=now.year - 1).isoformat()
            params["timeMax"] = now.replace(year=now.year + 2).isoformat()

        next_sync_token = None
        while True:
            request_params = dict(params)
            if page_token:
                request_params["pageToken"] = page_token
            try:
                response = service.events().list(**request_params).execute()
            except HttpError as e:
                if e.resp.status == 410:
                    raise GoogleSyncTokenExpired()
                raise
            events.extend(response.get("items", []))
            next_sync_token = response.get("nextSyncToken", next_sync_token)
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return events, next_sync_token

    def watch_events(self, channel_id: str, webhook_url: str) -> dict:
        service = self._get_service()
        return (
            service.events()
            .watch(
                calendarId=self.account.calendar_id,
                body={"id": channel_id, "type": "web_hook", "address": webhook_url},
            )
            .execute()
        )

    def stop_channel(self, channel_id: str, resource_id: str) -> None:
        service = self._get_service()
        try:
            service.channels().stop(body={"id": channel_id, "resourceId": resource_id}).execute()
        except HttpError:
            pass  # channel may already be expired/stopped — safe to ignore
