import pytest
from fastapi import HTTPException

from app.models import Issue, ProjectRole
from app.schemas import MentionIn
from app.services.chat_service import ChatService
from tests.conftest import add_member, make_project, make_user


def _make_issue(db, project, reporter):
    issue = Issue(
        project_id=project.id,
        issue_number=1,
        issue_key=f"{project.key}-1",
        title="Sample issue",
        issue_type="Task",
        priority="Medium",
        status="To Do",
        reporter_id=reporter.id,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def test_create_message_persists_and_returns_unmasked(db_session):
    project = make_project(db_session, key="SVC")
    author = make_user(db_session, name="Author")
    add_member(db_session, project, author)

    out = ChatService(db_session).create_message(project.key, author, "hello team", [])

    assert out.body == "hello team"
    assert out.is_deleted is False
    assert out.author.id == author.id


def test_create_message_resolves_valid_user_mention_and_notifies(db_session):
    project = make_project(db_session, key="SVC2")
    author = make_user(db_session, name="Author2")
    mentioned = make_user(db_session, name="Mentioned")
    add_member(db_session, project, author)
    add_member(db_session, project, mentioned)

    out = ChatService(db_session).create_message(
        project.key, author, "hi @[user:2:Mentioned]", [MentionIn(type="user", id=mentioned.id)]
    )

    assert len(out.mentions) == 1
    assert out.mentions[0].type == "user"
    assert out.mentions[0].id == mentioned.id

    from app.services import NotificationService

    notifications = NotificationService(db_session).list_for_user(mentioned)
    assert len(notifications) == 1
    assert notifications[0].type == "chat_mention"


def test_create_message_drops_mention_for_non_member(db_session):
    project = make_project(db_session, key="SVC3")
    author = make_user(db_session, name="Author3")
    outsider = make_user(db_session, name="Outsider")
    add_member(db_session, project, author)
    # outsider is NOT added as a member of `project`

    out = ChatService(db_session).create_message(
        project.key, author, "hi @[user:x:Outsider]", [MentionIn(type="user", id=outsider.id)]
    )

    assert out.mentions == []


def test_create_message_resolves_issue_mention_in_same_project(db_session):
    project = make_project(db_session, key="SVC4")
    author = make_user(db_session, name="Author4")
    add_member(db_session, project, author)
    issue = _make_issue(db_session, project, author)

    out = ChatService(db_session).create_message(
        project.key, author, "see #[issue:1:SVC4-1]", [MentionIn(type="issue", id=issue.id)]
    )

    assert len(out.mentions) == 1
    assert out.mentions[0].type == "issue"
    assert out.mentions[0].label == "SVC4-1"


def test_edit_message_requires_author(db_session):
    project = make_project(db_session, key="SVC5")
    author = make_user(db_session, name="Author5")
    other = make_user(db_session, name="Other")
    add_member(db_session, project, author)
    add_member(db_session, project, other)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "original", [])

    with pytest.raises(HTTPException) as exc_info:
        service.edit_message(project.key, message.id, other, "hacked", [])
    assert exc_info.value.status_code == 403


def test_edit_message_does_not_renotify_existing_mention(db_session):
    project = make_project(db_session, key="SVC6")
    author = make_user(db_session, name="Author6")
    mentioned = make_user(db_session, name="Mentioned6")
    add_member(db_session, project, author)
    add_member(db_session, project, mentioned)
    service = ChatService(db_session)
    message = service.create_message(
        project.key, author, "hi @[user:2:Mentioned6]", [MentionIn(type="user", id=mentioned.id)]
    )

    service.edit_message(
        project.key, message.id, author, "hi again @[user:2:Mentioned6]",
        [MentionIn(type="user", id=mentioned.id)],
    )

    from app.services import NotificationService

    notifications = NotificationService(db_session).list_for_user(mentioned)
    assert len(notifications) == 1  # still just the one from creation, not a second from the edit


def test_delete_message_masks_body_and_strips_mentions(db_session):
    project = make_project(db_session, key="SVC7")
    author = make_user(db_session, name="Author7")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "secret content", [])

    out = service.delete_message(project.key, message.id, author)

    assert out.is_deleted is True
    assert out.body == "[message deleted]"
    assert out.mentions == []


def test_delete_message_allowed_for_project_lead_not_random_member(db_session):
    project = make_project(db_session, key="SVC8")
    author = make_user(db_session, name="Author8")
    lead = make_user(db_session, name="Lead8")
    other_member = make_user(db_session, name="Member8")
    add_member(db_session, project, author)
    add_member(db_session, project, lead, role=ProjectRole.Lead)
    add_member(db_session, project, other_member)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "will be deleted", [])

    with pytest.raises(HTTPException) as exc_info:
        service.delete_message(project.key, message.id, other_member)
    assert exc_info.value.status_code == 403

    out = service.delete_message(project.key, message.id, lead)
    assert out.is_deleted is True


def test_list_messages_masks_deleted_for_members(db_session):
    project = make_project(db_session, key="SVC9")
    author = make_user(db_session, name="Author9")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "will be deleted", [])
    service.delete_message(project.key, message.id, author)

    messages = service.list_messages(project.key, author, before_id=None, limit=50)

    assert messages[0].body == "[message deleted]"


def test_list_messages_for_admin_shows_real_body_of_deleted_message(db_session):
    project = make_project(db_session, key="SVC10")
    author = make_user(db_session, name="Author10")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "secret admin-visible content", [])
    service.delete_message(project.key, message.id, author)

    admin_messages = service.list_messages_for_admin(project.id, before_id=None, limit=50)

    assert admin_messages[0].is_deleted is True
    assert admin_messages[0].body == "secret admin-visible content"


def test_list_projects_for_admin_reports_last_message_at(db_session):
    project = make_project(db_session, key="SVC11")
    author = make_user(db_session, name="Author11")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    service.create_message(project.key, author, "hi", [])

    summaries = service.list_projects_for_admin()
    summary = next(s for s in summaries if s.key == "SVC11")
    assert summary.last_message_at is not None
