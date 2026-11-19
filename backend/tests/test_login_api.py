def test_login_session_and_logout_work_through_api(client, app_module):
    registration = client.post(
        "/api/register",
        json={"email": "researcher@example.com", "password": "test-password"},
    )
    assert registration.json()["success"] is True

    login = client.post(
        "/api/login",
        json={"email": " RESEARCHER@example.com ", "password": "test-password"},
    )

    assert login.status_code == 200
    login_data = login.json()
    assert login_data["success"] is True
    assert login_data["user"]["email"] == "researcher@example.com"
    assert login_data["token"]

    headers = {"Authorization": f"Bearer {login_data['token']}"}
    session = client.get("/api/session", headers=headers)
    assert session.status_code == 200
    assert session.json()["user"] == login_data["user"]

    conn = app_module.get_db()
    activity_count = conn.execute(
        "SELECT COUNT(*) FROM login_activity WHERE email = ?",
        ("researcher@example.com",),
    ).fetchone()[0]
    conn.close()
    assert activity_count == 1

    logout = client.post("/api/logout", headers=headers)
    assert logout.status_code == 200
    assert logout.json() == {"success": True}
    assert client.get("/api/session", headers=headers).status_code == 401


def test_failed_login_does_not_create_session_or_activity(client, app_module):
    client.post(
        "/api/register",
        json={"email": "researcher@example.com", "password": "test-password"},
    )

    login = client.post(
        "/api/login",
        json={"email": "researcher@example.com", "password": "wrong-password"},
    )

    assert login.status_code == 200
    assert login.json() == {
        "success": False,
        "message": "Invalid email or password.",
    }

    conn = app_module.get_db()
    session_count = conn.execute("SELECT COUNT(*) FROM auth_sessions").fetchone()[0]
    activity_count = conn.execute("SELECT COUNT(*) FROM login_activity").fetchone()[0]
    conn.close()
    assert session_count == 0
    assert activity_count == 0
