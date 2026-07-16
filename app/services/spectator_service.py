from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories import SpectatorAccessRepository
from app.schemas import SpectatorViewOut
from app.services.issue_service import IssueService

SPECTATOR_VIEW_LIMIT = 10

# Common disposable/throwaway email providers — a lightweight "is this a
# real address" gate, not exhaustive.
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com",
    "tempmail.com",
    "temp-mail.org",
    "guerrillamail.com",
    "guerrillamail.info",
    "10minutemail.com",
    "10minutemail.net",
    "yopmail.com",
    "throwawaymail.com",
    "trashmail.com",
    "getnada.com",
    "fakeinbox.com",
    "sharklasers.com",
    "dispostable.com",
    "maildrop.cc",
    "mintemail.com",
}


class SpectatorService:
    def __init__(self, db: Session):
        self.db = db
        self.accesses = SpectatorAccessRepository(db)
        self.issue_service = IssueService(db)

    def view_issue(self, issue_key: str, name: str, email: str) -> SpectatorViewOut:
        name = name.strip()
        email = email.strip().lower()
        domain = email.rsplit("@", 1)[-1]
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise HTTPException(
                status_code=422,
                detail="Please use a permanent email address, not a disposable one.",
            )

        # Look the issue up first so a typo'd link doesn't burn one of the
        # visitor's limited views.
        detail = self.issue_service.get_issue_public(issue_key)

        access = self.accesses.get_by_email(email)
        if access is None:
            access = self.accesses.create(name=name, email=email)
        elif access.view_count >= SPECTATOR_VIEW_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"You've used all {SPECTATOR_VIEW_LIMIT} free ticket views for this email. "
                    "Please register for a full account to keep viewing tickets."
                ),
            )
        else:
            access.name = name

        access.view_count += 1
        access.last_seen_at = datetime.utcnow()
        self.accesses.save()

        return SpectatorViewOut(
            issue=detail,
            views_used=access.view_count,
            views_remaining=max(SPECTATOR_VIEW_LIMIT - access.view_count, 0),
            view_limit=SPECTATOR_VIEW_LIMIT,
        )
