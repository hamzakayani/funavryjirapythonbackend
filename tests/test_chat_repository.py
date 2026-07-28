# backend/tests/test_chat_repository.py
from app.models import ChatMessage
from app.repositories import ChatRepository
from tests.conftest import make_project, make_user


def test_list_for_project_is_newest_first_and_paginates(db_session):
    author = make_user(db_session, name="Author")
    project = make_project(db_session, key="RPO")
    repo = ChatRepository(db_session)

    ids = []
    for i in range(5):
        message = ChatMessage(project_id=project.id, author_id=author.id, body=f"msg {i}")
        repo.create(message)
        repo.save()
        ids.append(message.id)

    first_page = repo.list_for_project(project.id, limit=3)
    assert [m.id for m in first_page] == list(reversed(ids))[:3]

    second_page = repo.list_for_project(project.id, before_id=first_page[-1].id, limit=3)
    assert [m.id for m in second_page] == list(reversed(ids))[3:]


def test_last_message_at_returns_none_when_no_messages(db_session):
    project = make_project(db_session, key="RPO2")
    repo = ChatRepository(db_session)
    assert repo.last_message_at(project.id) is None


def test_get_by_id_scopes_to_project(db_session):
    author = make_user(db_session, name="Author2")
    project_a = make_project(db_session, key="RPOA")
    project_b = make_project(db_session, key="RPOB")
    repo = ChatRepository(db_session)
    message = ChatMessage(project_id=project_a.id, author_id=author.id, body="hi")
    repo.create(message)
    repo.save()

    assert repo.get_by_id(message.id, project_a.id) is not None
    assert repo.get_by_id(message.id, project_b.id) is None
