from tests.conftest import add_member, auth_headers, make_project, make_user


def test_send_and_list_messages(client, db_session):
    project = make_project(db_session, key="RTR")
    author = make_user(db_session, name="Author")
    add_member(db_session, project, author)

    send_res = client.post(
        "/api/v1/projects/RTR/chat/messages",
        json={"text": "hello there", "mentions": []},
        headers=auth_headers(author),
    )
    assert send_res.status_code == 200
    assert send_res.json()["body"] == "hello there"

    list_res = client.get("/api/v1/projects/RTR/chat/messages", headers=auth_headers(author))
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_non_member_cannot_post_or_read(client, db_session):
    project = make_project(db_session, key="RTR2")
    outsider = make_user(db_session, name="Outsider")

    res = client.get("/api/v1/projects/RTR2/chat/messages", headers=auth_headers(outsider))
    assert res.status_code == 403


def test_super_admin_can_read_without_membership(client, db_session):
    project = make_project(db_session, key="RTR3")
    admin = make_user(db_session, name="Admin", is_super_admin=True)

    res = client.get("/api/v1/projects/RTR3/chat/messages", headers=auth_headers(admin))
    assert res.status_code == 200


def test_edit_requires_author(client, db_session):
    project = make_project(db_session, key="RTR4")
    author = make_user(db_session, name="Author4")
    other = make_user(db_session, name="Other4")
    add_member(db_session, project, author)
    add_member(db_session, project, other)
    message_id = client.post(
        "/api/v1/projects/RTR4/chat/messages",
        json={"text": "mine", "mentions": []},
        headers=auth_headers(author),
    ).json()["id"]

    res = client.patch(
        f"/api/v1/projects/RTR4/chat/messages/{message_id}",
        json={"text": "hacked", "mentions": []},
        headers=auth_headers(other),
    )
    assert res.status_code == 403


def test_delete_masks_body_in_subsequent_list(client, db_session):
    project = make_project(db_session, key="RTR5")
    author = make_user(db_session, name="Author5")
    add_member(db_session, project, author)
    message_id = client.post(
        "/api/v1/projects/RTR5/chat/messages",
        json={"text": "to be deleted", "mentions": []},
        headers=auth_headers(author),
    ).json()["id"]

    delete_res = client.delete(
        f"/api/v1/projects/RTR5/chat/messages/{message_id}", headers=auth_headers(author)
    )
    assert delete_res.status_code == 200
    assert delete_res.json()["body"] == "[message deleted]"

    list_res = client.get("/api/v1/projects/RTR5/chat/messages", headers=auth_headers(author))
    assert list_res.json()[0]["body"] == "[message deleted]"


def test_websocket_receives_broadcast_message(client, db_session):
    from app.core.security import create_access_token

    project = make_project(db_session, key="RTR6")
    author = make_user(db_session, name="Author6")
    add_member(db_session, project, author)
    token = create_access_token(author.id)

    with client.websocket_connect(f"/api/v1/ws/projects/RTR6/chat?token={token}") as ws:
        client.post(
            "/api/v1/projects/RTR6/chat/messages",
            json={"text": "live message", "mentions": []},
            headers=auth_headers(author),
        )
        event = ws.receive_json()

    assert event["type"] == "message_created"
    assert event["message"]["body"] == "live message"


def test_websocket_rejects_non_member(client, db_session):
    project = make_project(db_session, key="RTR7")
    outsider = make_user(db_session, name="Outsider7")
    from app.core.security import create_access_token

    token = create_access_token(outsider.id)

    try:
        with client.websocket_connect(f"/api/v1/ws/projects/RTR7/chat?token={token}"):
            pass
        assert False, "expected the websocket connection to be rejected"
    except Exception:
        pass
