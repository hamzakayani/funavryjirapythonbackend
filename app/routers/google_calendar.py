from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/google", tags=["google-calendar"])
oauth_service = GoogleOAuthService()


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

    repo.save()

    frontend_base = settings.frontend_url.rstrip("/")
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
