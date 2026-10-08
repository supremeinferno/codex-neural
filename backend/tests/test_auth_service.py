from backend.services.auth_service import authenticate_user, create_session, get_session, init_db, register_user


def test_register_and_login_user(tmp_path, monkeypatch):
    import backend.services.auth_service as auth_service
    from backend.repositories import sqlite_repository

    monkeypatch.setattr(sqlite_repository, "DB_PATH", tmp_path / "auth_service_test.db")
    auth_service.init_db()

    ok, message = auth_service.register_user(" user@example.com ", "StrongPass!123")
    assert ok is True
    assert message == "Account created successfully."
    conn = sqlite_repository.get_db()
    created_at = conn.execute(
        "SELECT created_at FROM users WHERE email = ?",
        ("user@example.com",),
    ).fetchone()["created_at"]
    conn.close()
    assert created_at

    user = auth_service.authenticate_user("user@example.com", "StrongPass!123")
    assert user is not None
    assert user["email"] == "user@example.com"

    session_id, expires_at = auth_service.create_session(user["id"], user["email"])
    assert session_id
    assert expires_at > 0

    session = auth_service.get_session(session_id)
    assert session is not None
    assert session["email"] == "user@example.com"


def test_password_reset_persists_and_consumes_otp(tmp_path, monkeypatch):
    import backend.services.auth_service as auth_service
    from backend.repositories import sqlite_repository

    monkeypatch.setattr(sqlite_repository, "DB_PATH", tmp_path / "password_reset.db")
    auth_service.init_db()
    auth_service.register_user("user@example.com", "StrongPass!123")

    sent = {}
    monkeypatch.setattr(
        auth_service,
        "send_otp_email",
        lambda email, otp: sent.update({"email": email, "otp": otp}),
    )

    requested, _ = auth_service.request_password_reset(" USER@example.com ")
    verified, _ = auth_service.verify_otp("user@example.com", sent["otp"])
    reset, _ = auth_service.reset_password(
        "user@example.com",
        sent["otp"],
        "ChangedPass!456",
    )
    otp_after_reset = sqlite_repository.get_password_reset_otp("user@example.com")

    assert requested is True
    assert verified is True
    assert reset is True
    assert otp_after_reset is None
    assert auth_service.authenticate_user("user@example.com", "ChangedPass!456")
