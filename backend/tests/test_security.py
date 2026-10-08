from backend.security import (
    LoginAttemptTracker,
    is_password_strong_enough,
    is_session_active,
    normalize_email,
)


def test_normalize_email_handles_whitespace_and_case():
    assert normalize_email("  USER@Example.com ") == "user@example.com"


def test_password_strength_requires_length_and_complexity():
    assert is_password_strong_enough("short") is False
    assert is_password_strong_enough("StrongPass!123") is True


def test_login_attempt_tracker_blocks_after_threshold():
    tracker = LoginAttemptTracker(max_attempts=3, window_seconds=60)

    assert tracker.allow("1.2.3.4", "alice@example.com") is True
    assert tracker.allow("1.2.3.4", "alice@example.com") is True
    assert tracker.allow("1.2.3.4", "alice@example.com") is True
    assert tracker.allow("1.2.3.4", "alice@example.com") is False

    tracker.clear("1.2.3.4", "alice@example.com")
    assert tracker.allow("1.2.3.4", "alice@example.com") is True


def test_session_helper_handles_expiry_checks():
    assert is_session_active(200, now=100) is True
    assert is_session_active(200, now=200) is False
    assert is_session_active(None, now=100) is False
