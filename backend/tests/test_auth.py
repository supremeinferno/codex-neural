from backend import auth


def test_registration_normalizes_email_and_rejects_duplicate():
    created, _ = auth.register_user("  RESEARCHER@example.com ", "test-password")

    assert created is True
    authenticated_user = auth.authenticate_user(
        "researcher@example.com",
        "test-password",
    )
    assert authenticated_user["email"] == "researcher@example.com"

    duplicate, message = auth.register_user(
        "researcher@example.com",
        "another-password",
    )
    assert duplicate is False
    assert "already exists" in message


def test_registration_rejects_short_password():
    created, message = auth.register_user("short@example.com", "123")

    assert created is False
    assert "at least" in message


def test_session_can_be_revoked():
    auth.register_user("session@example.com", "test-password")
    user = auth.authenticate_user("session@example.com", "test-password")
    token = auth.create_session(user["id"])

    assert auth.get_user_for_session(token) == user

    auth.revoke_session(token)

    assert auth.get_user_for_session(token) is None
