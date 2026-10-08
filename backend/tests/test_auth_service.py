from backend.services.auth_service import authenticate_user, create_session, get_session, init_db, register_user


def test_register_and_login_user(tmp_path, monkeypatch):
    import backend.services.auth_service as auth_service

    monkeypatch.setattr(auth_service, "DB_PATH", tmp_path / "auth_service_test.db")
    auth_service.init_db()

    ok, message = auth_service.register_user(" user@example.com ", "StrongPass!123")
    assert ok is True
    assert message == "Account created successfully."

    user = auth_service.authenticate_user("user@example.com", "StrongPass!123")
    assert user is not None
    assert user["email"] == "user@example.com"

    session_id, expires_at = auth_service.create_session(user["id"], user["email"])
    assert session_id
    assert expires_at > 0

    session = auth_service.get_session(session_id)
    assert session is not None
    assert session["email"] == "user@example.com"
