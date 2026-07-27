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


def renew_expiring_watch_channels_job() -> None:
    from datetime import datetime, timedelta
    import uuid

    from app.services.google_calendar_client import GoogleCalendarClient

    db = SessionLocal()
    try:
        repo = GoogleAccountRepository(db)
        soon = datetime.utcnow() + timedelta(hours=24)
        for account in repo.list_connected():
            if not account.channel_expiration or account.channel_expiration > soon:
                continue
            try:
                client = GoogleCalendarClient(account, db)
                if account.channel_id and account.resource_id:
                    client.stop_channel(account.channel_id, account.resource_id)
                new_channel_id = str(uuid.uuid4())
                watch_response = client.watch_events(new_channel_id, settings.google_calendar_webhook_url)
                account.channel_id = new_channel_id
                account.resource_id = watch_response.get("resourceId")
                expiration_ms = watch_response.get("expiration")
                if expiration_ms:
                    account.channel_expiration = datetime.utcfromtimestamp(int(expiration_ms) / 1000)
                repo.save()
            except Exception:
                logger.exception("Watch channel renewal failed for user_id=%s", account.user_id)
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
    if settings.enable_google_watch:
        scheduler.add_job(
            renew_expiring_watch_channels_job,
            "interval",
            hours=1,
            id="google_watch_renew",
            max_instances=1,
            coalesce=True,
            replace_existing=True,
        )
    scheduler.start()


def shutdown_scheduler() -> None:
    scheduler.shutdown(wait=False)
