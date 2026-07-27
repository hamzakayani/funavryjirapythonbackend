from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:password@localhost:3306/jira_clone"
    secret_key: str = "change-me-in-production-use-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:3000"
    frontend_url: str = "https://funavryjirafrontend.vercel.app"
    upload_dir: str = "uploads"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/google/callback"
    google_calendar_webhook_url: str = ""
    enable_google_watch: bool = False
    token_encryption_key: str = ""
    google_sync_poll_interval_minutes: int = 5
    # In a multi-worker deployment (e.g. gunicorn -w N) this MUST be true on
    # exactly ONE worker/process, otherwise every worker runs its own poller.
    scheduler_enabled: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
