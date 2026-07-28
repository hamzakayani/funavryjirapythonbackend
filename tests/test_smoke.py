from tests.conftest import add_member, auth_headers, make_project, make_user


def test_health_check_needs_no_auth(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_authenticated_project_list(client, db_session):
    user = make_user(db_session, name="Alice")
    project = make_project(db_session, key="SMK")
    add_member(db_session, project, user)

    res = client.get("/api/v1/projects", headers=auth_headers(user))

    assert res.status_code == 200
    keys = [p["key"] for p in res.json()]
    assert "SMK" in keys
