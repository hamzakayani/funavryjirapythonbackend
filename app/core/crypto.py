from cryptography.fernet import Fernet

from app.config import settings


def _fernet() -> Fernet:
    if not settings.token_encryption_key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not configured")
    return Fernet(settings.token_encryption_key.encode())


def encrypt_token(raw: str) -> str:
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _fernet().decrypt(encrypted.encode()).decode()
