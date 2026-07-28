# backend/tests/test_chat_models.py
from app.models import ChatAttachment, ChatMessage, ChatMessageMention
from tests.conftest import make_project, make_user


def test_chat_message_with_mention_and_attachment(db_session):
    author = make_user(db_session, name="Author")
    mentioned = make_user(db_session, name="Mentioned")
    project = make_project(db_session, key="CHT")

    message = ChatMessage(project_id=project.id, author_id=author.id, body="hello @[user:2:Mentioned]")
    message.mentions.append(ChatMessageMention(mentioned_user_id=mentioned.id))
    message.attachments.append(
        ChatAttachment(
            stored_filename="abc.pdf",
            original_filename="notes.pdf",
            content_type="application/pdf",
            file_size=1234,
        )
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)

    assert message.id is not None
    assert message.is_edited is False
    assert message.is_deleted is False
    assert len(message.mentions) == 1
    assert message.mentions[0].mentioned_user_id == mentioned.id
    assert len(message.attachments) == 1
    assert message.attachments[0].original_filename == "notes.pdf"


def test_deleting_message_cascades_mentions_and_attachments(db_session):
    author = make_user(db_session, name="Author2")
    project = make_project(db_session, key="CHT2")
    message = ChatMessage(project_id=project.id, author_id=author.id, body="temp")
    message.mentions.append(ChatMessageMention(mentioned_user_id=author.id))
    db_session.add(message)
    db_session.commit()
    message_id = message.id

    db_session.delete(message)
    db_session.commit()

    assert db_session.query(ChatMessageMention).filter_by(message_id=message_id).count() == 0
