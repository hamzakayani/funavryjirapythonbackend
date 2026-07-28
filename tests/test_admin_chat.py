from tests.conftest import add_member, auth_headers, make_project, make_user


def test_admin_chat_projects_lists_all_projects(client, db_session):
    admin = make_user(db_session, name="Admin", is_super_admin=True)
    make_project(db_session, key="ADM")

    res = client.get("/api/v1/admin/chat/projects", headers=auth_headers(admin))

    assert res.status_code == 200
    assert any(p["key"] == "ADM" for p in res.json())


def test_admin_chat_projects_rejects_non_admin(client, db_session):
    user = make_user(db_session, name="Regular")

    res = client.get("/api/v1/admin/chat/projects", headers=auth_headers(user))

    assert res.status_code == 403


def test_admin_can_see_real_body_of_deleted_message(client, db_session):
    admin = make_user(db_session, name="Admin2", is_super_admin=True)
    author = make_user(db_session, name="Author")
    project = make_project(db_session, key="ADM2")
    add_member(db_session, project, author)

    message_id = client.post(
        "/api/v1/projects/ADM2/chat/messages",
        json={"text": "sensitive content", "mentions": []},
        headers=auth_headers(author),
    ).json()["id"]
    client.delete(f"/api/v1/projects/ADM2/chat/messages/{message_id}", headers=auth_headers(author))

    res = client.get(f"/api/v1/admin/chat/projects/{project.id}/messages", headers=auth_headers(admin))

    assert res.status_code == 200
    assert res.json()[0]["is_deleted"] is True
    assert res.json()[0]["body"] == "sensitive content"
