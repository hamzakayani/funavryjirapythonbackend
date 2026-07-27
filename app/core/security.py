from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_access_token(token: str) -> int:
    """Return user_id from JWT or raise JWTError/ValueError.

    Normal login tokens (minted by create_access_token) never carry a
    `purpose` claim, so rejecting any token that does have one prevents
    purpose-scoped tokens (e.g. the OAuth state token) from being replayed
    here as a regular Bearer login credential, without affecting any
    existing login token.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("purpose") is not None:
        raise ValueError("Token not valid for login use")
    return int(payload.get("sub"))


OAUTH_STATE_PURPOSE = "google_oauth_state"
OAUTH_STATE_EXPIRE_MINUTES = 10


def create_oauth_state_token(user_id: int) -> str:
    """Mint a short-lived, purpose-scoped token for use as an OAuth `state`
    value only. Distinct from create_access_token: shorter expiry and a
    `purpose` claim that prevents it from being replayed as a normal login
    Bearer token via decode_access_token/get_current_user.
    """
    expire = datetime.utcnow() + timedelta(minutes=OAUTH_STATE_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "purpose": OAUTH_STATE_PURPOSE, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_oauth_state_token(token: str) -> int:
    """Return user_id from an OAuth state token or raise JWTError/ValueError
    if invalid, expired, or missing the expected `purpose` claim.
    """
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    if payload.get("purpose") != OAUTH_STATE_PURPOSE:
        raise ValueError("Invalid token purpose")
    return int(payload.get("sub"))
