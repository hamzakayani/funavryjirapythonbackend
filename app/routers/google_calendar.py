import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.crypto import encrypt_token
from app.core.deps import get_current_user
from app.core.security import create_oauth_state_token, decode_oauth_state_token
from app.database import get_db
from app.models import GoogleAccount, User
from app.repositories import GoogleAccountRepository
from app.schemas import GoogleAccountStatusOut, GoogleAuthorizationUrlOut
from app.services.google_oauth_service import GoogleOAuthService
from app.services.google_sync_service import GoogleSyncService

router = APIRouter(prefix="/google", tags=["google-calendar"])
oauth_service = GoogleOAuthService()
logger = logging.getLogger(__name__)


@router.get("/connect", response_model=GoogleAuthorizationUrlOut)
def connect(user: User = Depends(get_current_user)):
    # Mint a short-lived, purpose-scoped state token (NOT the app's normal login
    # JWT) so the callback (which Google calls directly, with no Authorization
    # header) knows which app user to link. This token cannot be replayed as a
    # normal Bearer credential and expires in ~10 minutes instead of 24 hours.
    state = create_oauth_state_token(user.id)
    return GoogleAuthorizationUrlOut(authorization_url=oauth_service.get_authorization_url(state))


@router.get("/callback")
def callback(code: str = Query(...), state: str = Query(...), db: Session = Depends(get_db)):
    try:
        user_id = decode_oauth_state_token(state)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    frontend_base = settings.frontend_url.rstrip("/")

    try:
        creds = oauth_service.exchange_code(code)

        repo = GoogleAccountRepository(db)
        account = repo.get_by_user_id(user_id)
        if not account:
            account = GoogleAccount(
                user_id=user_id,
                google_email="",
                access_token="",
                refresh_token="",
                token_expiry=creds.expiry,
                scope=" ".join(creds.scopes or []),
            )
            repo.create(account)

        oauth_service.persist_credentials(account, creds)
        account.is_connected = True

        # Fetch the connected Google account's email for display purposes.
        from googleapiclient.discovery import build

        try:
            oauth2_service = build("oauth2", "v2", credentials=creds)
            info = oauth2_service.userinfo().get().execute()
            account.google_email = info.get("email", "")
        except Exception:
            pass  # non-fatal — calendar access itself doesn't require this

        if settings.enable_google_watch and settings.google_calendar_webhook_url:
            import uuid
            from app.services.google_calendar_client import GoogleCalendarClient

            try:
                channel_id = str(uuid.uuid4())
                client = GoogleCalendarClient(account, db)
                watch_response = client.watch_events(channel_id, settings.google_calendar_webhook_url)
                account.channel_id = channel_id
                account.resource_id = watch_response.get("resourceId")
                expiration_ms = watch_response.get("expiration")
                if expiration_ms:
                    from datetime import datetime
                    account.channel_expiration = datetime.utcfromtimestamp(int(expiration_ms) / 1000)
            except Exception:
                # Best-effort: watch registration is a latency optimization on
                # top of the 5-minute poller, never a requirement for the
                # connection itself (e.g. it fails if the webhook domain
                # isn't verified with Google). The account must still get
                # saved below regardless.
                logger.exception(
                    "Google watch channel registration failed for user_id=%s", user_id
                )

        repo.save()
    except Exception:
        # Anything else here (invalid/expired/reused code, redirect_uri
        # mismatch, transient Google API error, DB error) must never crash
        # as a bare 500 — log the full traceback server-side for diagnosis,
        # and send the user back to a page that can actually tell them it
        # failed instead of a blank "Internal Server Error".
        logger.exception("Google OAuth callback failed for user_id=%s", user_id)
        return RedirectResponse(url=f"{frontend_base}/profile?error=1")

    return RedirectResponse(url=f"{frontend_base}/profile?connected=1")


@router.post("/disconnect")
def disconnect(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = GoogleAccountRepository(db)
    account = repo.get_by_user_id(user.id)
    if account:
        repo.delete(account)
        repo.save()
    return {"message": "Disconnected"}


@router.get("/status", response_model=GoogleAccountStatusOut)
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = GoogleAccountRepository(db).get_by_user_id(user.id)
    if not account or not account.is_connected:
        return GoogleAccountStatusOut(connected=False)
    return GoogleAccountStatusOut(
        connected=True,
        google_email=account.google_email,
        calendar_id=account.calendar_id,
        last_synced_at=account.last_synced_at,
    )


@router.post("/sync-now")
def sync_now(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = GoogleAccountRepository(db).get_by_user_id(user.id)
    if not account or not account.is_connected:
        raise HTTPException(status_code=400, detail="Google account not connected")
    count = GoogleSyncService(db).pull_sync_for_account(account)
    return {"synced_events": count}


@router.post("/webhook")
def webhook(
    x_goog_channel_id: str | None = Header(default=None),
    x_goog_resource_state: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Google calls this with no body and no auth — only headers identifying
    the channel. Payload never contains event data, only a 'something
    changed' signal; we look up the matching account by channel_id and run
    the same incremental pull the poller uses."""
    if not x_goog_channel_id or x_goog_resource_state == "sync":
        return {"ok": True}  # initial sync handshake, no action needed
    account = (
        db.query(GoogleAccount)
        .filter(GoogleAccount.channel_id == x_goog_channel_id, GoogleAccount.is_connected.is_(True))
        .first()
    )
    if account:
        GoogleSyncService(db).pull_sync_for_account(account)
    return {"ok": True}
