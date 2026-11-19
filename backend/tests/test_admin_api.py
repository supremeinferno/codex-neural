def test_admin_routes_require_admin_session(client, user_factory, app_module):
    regular_headers, _ = user_factory("regular@example.com")

    assert client.get("/api/admin/dashboard").status_code == 401
    response = client.get("/api/admin/dashboard", headers=regular_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access required."


def test_admin_cannot_delete_admin_and_can_delete_user_and_login_history(
    app_module,
    client,
    user_factory,
):
    admin_headers, admin_id = user_factory(app_module.ADMIN_EMAIL)
    user_headers, user_id = user_factory("remove@example.com")
    login = client.post(
        "/api/login",
        json={"email": "remove@example.com", "password": "test-password"},
    )
    assert login.json()["success"] is True

    conn = app_module.get_db()
    admin_row = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        (app_module.ADMIN_EMAIL,),
    ).fetchone()
    activity_row = conn.execute(
        "SELECT id FROM login_activity WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    assert admin_row["id"] == admin_id

    protected = client.delete(
        f"/api/admin/users/{admin_id}",
        headers=admin_headers,
    )
    assert protected.status_code == 403

    deleted = client.delete(
        f"/api/admin/users/{user_id}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["success"] is True
    assert client.get("/api/session", headers=user_headers).status_code == 401

    conn = app_module.get_db()
    assert conn.execute(
        "SELECT COUNT(*) FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()[0] == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM login_activity WHERE user_id = ?",
        (user_id,),
    ).fetchone()[0] == 0
    conn.close()

    missing_activity = client.delete(
        f"/api/admin/logins/{activity_row['id']}",
        headers=admin_headers,
    )
    assert missing_activity.status_code == 404


def test_admin_can_delete_single_login_and_clear_remaining_history(
    app_module,
    client,
    user_factory,
):
    admin_headers, _ = user_factory(app_module.ADMIN_EMAIL)
    client.post(
        "/api/register",
        json={"email": "login-user@example.com", "password": "test-password"},
    )
    client.post(
        "/api/login",
        json={"email": "login-user@example.com", "password": "test-password"},
    )
    client.post(
        "/api/login",
        json={"email": "login-user@example.com", "password": "test-password"},
    )

    conn = app_module.get_db()
    activity_ids = [
        row["id"]
        for row in conn.execute(
            "SELECT id FROM login_activity ORDER BY id"
        ).fetchall()
    ]
    conn.close()
    assert len(activity_ids) == 2

    deleted = client.delete(
        f"/api/admin/logins/{activity_ids[0]}",
        headers=admin_headers,
    )
    assert deleted.status_code == 200

    cleared = client.delete("/api/admin/logins", headers=admin_headers)
    assert cleared.status_code == 200
    assert cleared.json()["deleted"] == 1

    conn = app_module.get_db()
    count = conn.execute("SELECT COUNT(*) FROM login_activity").fetchone()[0]
    conn.close()
    assert count == 0


def test_non_admin_cannot_mutate_admin_resources(client, user_factory):
    regular_headers, _ = user_factory("regular@example.com")

    response = client.delete(
        "/api/admin/logins",
        headers=regular_headers,
    )

    assert response.status_code == 403
