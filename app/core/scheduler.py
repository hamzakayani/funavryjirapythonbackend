import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.repositories import GoogleAccountRepository
from app.services.google_sync_service import GoogleSyncService

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def poll_all_google_accounts_job() -> None:
    db = SessionLocal()
    try:
        repo = GoogleAccountRepository(db)
        sync_service = GoogleSyncService(db)
        for account in repo.list_connected():
            try:
                sync_service.pull_sync_for_account(account)
            except Exception as exc:
                logger.exception("Google pull-sync failed for user_id=%s", account.user_id)
                if "invalid_grant" in str(exc):
                    account.is_connected = False
                    repo.save()
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        poll_all_google_accounts_job,
        "interval",
        minutes=settings.google_sync_poll_interval_minutes,
        id="google_poll_sync",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    scheduler.shutdown(wait=False)
