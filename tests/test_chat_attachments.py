import io

import pytest
from fastapi import HTTPException, UploadFile

from app.services.chat_service import ChatService
from tests.conftest import add_member, auth_headers, make_project, make_user


def _upload_file(content: bytes, filename: str = "notes.pdf", content_type: str = "application/pdf"):
    return UploadFile(filename=filename, file=io.BytesIO(content), headers={"content-type": content_type})


@pytest.mark.asyncio
async def test_add_attachment_persists_and_returns_file_url(db_session, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    project = make_project(db_session, key="ATT")
    author = make_user(db_session, name="Author")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "see attached", [])

    out = await service.add_attachment(project.key, message.id, _upload_file(b"pdf-bytes"), author)

    assert out.original_filename == "notes.pdf"
    assert out.content_type == "application/pdf"
    assert out.file_size == len(b"pdf-bytes")
    assert out.file_url == f"/api/v1/projects/ATT/chat/attachments/{out.id}/download"


@pytest.mark.asyncio
async def test_add_attachment_rejects_non_author(db_session, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    project = make_project(db_session, key="ATT2")
    author = make_user(db_session, name="Author2")
    other = make_user(db_session, name="Other2")
    add_member(db_session, project, author)
    add_member(db_session, project, other)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "mine", [])

    with pytest.raises(HTTPException) as exc_info:
        await service.add_attachment(project.key, message.id, _upload_file(b"data"), other)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_add_attachment_rejects_oversized_file(db_session, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    project = make_project(db_session, key="ATT3")
    author = make_user(db_session, name="Author3")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "big file incoming", [])

    oversized = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(HTTPException) as exc_info:
        await service.add_attachment(project.key, message.id, _upload_file(oversized), author)
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_download_attachment_sets_disposition_and_nosniff_headers(
    client, db_session, tmp_path, monkeypatch
):
    from app.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    project = make_project(db_session, key="ATT4")
    author = make_user(db_session, name="Author4")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "see attached", [])
    attachment_out = await service.add_attachment(
        project.key, message.id, _upload_file(b"<script>alert(1)</script>", filename="evil.html", content_type="text/html"), author
    )

    res = client.get(
        f"/api/v1/projects/{project.key}/chat/attachments/{attachment_out.id}/download",
        headers=auth_headers(author),
    )

    assert res.status_code == 200
    assert res.headers["x-content-type-options"] == "nosniff"
    assert "attachment" in res.headers["content-disposition"]
    assert "evil.html" in res.headers["content-disposition"]
    assert res.content == b"<script>alert(1)</script>"


@pytest.mark.asyncio
async def test_download_attachment_requires_project_access(client, db_session, tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    project = make_project(db_session, key="ATT5")
    author = make_user(db_session, name="Author5")
    outsider = make_user(db_session, name="Outsider5")
    add_member(db_session, project, author)
    service = ChatService(db_session)
    message = service.create_message(project.key, author, "see attached", [])
    attachment_out = await service.add_attachment(
        project.key, message.id, _upload_file(b"pdf-bytes"), author
    )

    res = client.get(
        f"/api/v1/projects/{project.key}/chat/attachments/{attachment_out.id}/download",
        headers=auth_headers(outsider),
    )

    assert res.status_code == 403
