from app.services import NotificationService
from tests.conftest import make_project, make_user


def test_notify_chat_mention_creates_notification_for_recipient(db_session):
    actor = make_user(db_session, name="Actor")
    recipient = make_user(db_session, name="Recipient")
    project = make_project(db_session, key="NTF")

    service = NotificationService(db_session)
    service.notify_chat_mention(project, actor, recipient.id)
    service.save()

    notifications = service.list_for_user(recipient)
    assert len(notifications) == 1
    assert notifications[0].type == "chat_mention"
    assert "chat" in notifications[0].message.lower()
    assert notifications[0].project_key == project.key


def test_notify_chat_mention_skips_self_mention(db_session):
    actor = make_user(db_session, name="Actor2")
    project = make_project(db_session, key="NTF2")

    service = NotificationService(db_session)
    service.notify_chat_mention(project, actor, actor.id)
    service.save()

    assert service.list_for_user(actor) == []
