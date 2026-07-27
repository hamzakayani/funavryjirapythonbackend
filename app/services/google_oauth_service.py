from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings
from app.core.crypto import decrypt_token, encrypt_token
from app.models import GoogleAccount

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


class GoogleOAuthService:
    def get_authorization_url(self, state: str) -> str:
        # PKCE is disabled: this is a confidential client (holds a
        # client_secret), so PKCE isn't required, and the code_verifier
        # google-auth-oauthlib would otherwise auto-generate here lives only
        # on this in-memory Flow instance — it can't survive to the /callback
        # request, which builds an entirely separate Flow. Without this flag
        # Google rejects the token exchange with "invalid_grant: Missing
        # code verifier".
        flow = Flow.from_client_config(
            _client_config(), scopes=SCOPES, state=state, autogenerate_code_verifier=False
        )
        flow.redirect_uri = settings.google_redirect_uri
        url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        return url

    def exchange_code(self, code: str) -> Credentials:
        flow = Flow.from_client_config(_client_config(), scopes=SCOPES)
        flow.redirect_uri = settings.google_redirect_uri
        flow.fetch_token(code=code)
        return flow.credentials

    def credentials_from_account(self, account: GoogleAccount) -> Credentials:
        creds = Credentials(
            token=decrypt_token(account.access_token),
            refresh_token=decrypt_token(account.refresh_token),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=SCOPES,
        )
        creds.expiry = account.token_expiry
        return creds

    def persist_credentials(self, account: GoogleAccount, creds: Credentials) -> None:
        account.access_token = encrypt_token(creds.token)
        if creds.refresh_token:
            account.refresh_token = encrypt_token(creds.refresh_token)
        account.token_expiry = creds.expiry or (datetime.utcnow() + timedelta(hours=1))
        account.scope = " ".join(creds.scopes or SCOPES)
