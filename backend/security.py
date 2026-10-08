from __future__ import annotations

import re
import time


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def is_password_strong_enough(password: str | None, min_length: int = 8) -> bool:
    if not isinstance(password, str):
        return False

    if len(password) < min_length:
        return False

    if not re.search(r"[A-Z]", password):
        return False

    if not re.search(r"[a-z]", password):
        return False

    if not re.search(r"\d", password):
        return False

    if not re.search(r"[^A-Za-z0-9]", password):
        return False

    return True


def is_session_active(expires_at: float | int | None, now: float | int | None = None) -> bool:
    if expires_at is None:
        return False

    current_time = float(now if now is not None else time.time())
    return current_time < float(expires_at)


class LoginAttemptTracker:
    def __init__(self, max_attempts: int = 5, window_seconds: int = 900, clock=None):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._clock = clock or time.time
        self._attempts = {}

    def _key(self, ip_address: str | None, email: str | None) -> str:
        return f"{ip_address or 'unknown'}:{normalize_email(email)}"

    def _clean(self, key: str):
        now = self._clock()
        attempts = [
            attempt_time
            for attempt_time in self._attempts.get(key, [])
            if now - attempt_time < self.window_seconds
        ]
        self._attempts[key] = attempts
        return attempts

    def allow(self, ip_address: str | None, email: str | None) -> bool:
        key = self._key(ip_address, email)
        attempts = self._clean(key)
        attempts.append(self._clock())
        self._attempts[key] = attempts
        return len(attempts) <= self.max_attempts

    def record_failure(self, ip_address: str | None, email: str | None) -> int:
        key = self._key(ip_address, email)
        attempts = self._clean(key)
        attempts.append(self._clock())
        self._attempts[key] = attempts
        return len(attempts)

    def clear(self, ip_address: str | None, email: str | None) -> None:
        self._attempts.pop(self._key(ip_address, email), None)
