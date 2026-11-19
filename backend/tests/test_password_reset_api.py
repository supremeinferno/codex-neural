from backend import auth


def test_password_reset_flow_replaces_password_and_consumes_otp(
    app_module,
    client,
    monkeypatch,
):
    registration = client.post(
        "/api/register",
        json={"email": "reset@example.com", "password": "old-password"},
    )
    assert registration.json()["success"] is True

    sent = {}
    monkeypatch.setattr(
        auth,
        "send_otp_email",
        lambda email, otp: sent.update(email=email, otp=otp),
    )

    requested = client.post(
        "/api/forgot-password",
        json={"email": " RESET@example.com "},
    )
    assert requested.json() == {
        "success": True,
        "message": "OTP sent successfully.",
    }
    assert sent["email"] == "reset@example.com"

    verified = client.post(
        "/api/verify-otp",
        json={"email": "reset@example.com", "otp": sent["otp"]},
    )
    assert verified.json()["success"] is True

    reset = client.post(
        "/api/reset-password",
        json={
            "email": "reset@example.com",
            "otp": sent["otp"],
            "new_password": "new-password",
        },
    )
    assert reset.json() == {
        "success": True,
        "message": "Password reset successfully.",
    }

    old_login = client.post(
        "/api/login",
        json={"email": "reset@example.com", "password": "old-password"},
    )
    new_login = client.post(
        "/api/login",
        json={"email": "reset@example.com", "password": "new-password"},
    )
    assert old_login.json()["success"] is False
    assert new_login.json()["success"] is True

    conn = app_module.get_db()
    otp_count = conn.execute(
        "SELECT COUNT(*) FROM password_reset_otps WHERE email = ?",
        ("reset@example.com",),
    ).fetchone()[0]
    conn.close()
    assert otp_count == 0


def test_password_reset_rejects_expired_otp_and_deletes_it(
    app_module,
    client,
    monkeypatch,
):
    client.post(
        "/api/register",
        json={"email": "expired@example.com", "password": "old-password"},
    )
    monkeypatch.setattr(auth, "send_otp_email", lambda _email, _otp: None)
    monkeypatch.setattr(auth.time, "time", lambda: 1_000)

    client.post(
        "/api/forgot-password",
        json={"email": "expired@example.com"},
    )
    conn = app_module.get_db()
    conn.execute(
        "UPDATE password_reset_otps SET expires = ? WHERE email = ?",
        (999, "expired@example.com"),
    )
    conn.commit()
    conn.close()

    response = client.post(
        "/api/verify-otp",
        json={"email": "expired@example.com", "otp": "123456"},
    )

    assert response.json() == {
        "success": False,
        "message": "OTP has expired.",
    }
    conn = app_module.get_db()
    otp_count = conn.execute(
        "SELECT COUNT(*) FROM password_reset_otps WHERE email = ?",
        ("expired@example.com",),
    ).fetchone()[0]
    conn.close()
    assert otp_count == 0


def test_password_reset_removes_otp_after_maximum_invalid_attempts(
    app_module,
    client,
    monkeypatch,
):
    client.post(
        "/api/register",
        json={"email": "attempts@example.com", "password": "old-password"},
    )
    monkeypatch.setattr(auth, "send_otp_email", lambda _email, _otp: None)
    client.post(
        "/api/forgot-password",
        json={"email": "attempts@example.com"},
    )

    for attempt in range(auth.OTP_MAX_ATTEMPTS):
        response = client.post(
            "/api/verify-otp",
            json={"email": "attempts@example.com", "otp": "wrong"},
        )
        assert response.json()["success"] is False

    conn = app_module.get_db()
    otp_count = conn.execute(
        "SELECT COUNT(*) FROM password_reset_otps WHERE email = ?",
        ("attempts@example.com",),
    ).fetchone()[0]
    conn.close()
    assert otp_count == 0

    response = client.post(
        "/api/verify-otp",
        json={"email": "attempts@example.com", "otp": "wrong"},
    )
    assert response.json()["message"] == "No OTP request found."
