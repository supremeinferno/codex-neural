from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_if_present() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception:
        # Keep local development resilient when python-dotenv is not installed.
        pass


@dataclass(frozen=True)
class Settings:
    smtp_email: str = "codexproject9@gmail.com"
    smtp_app_password: str = ""
    session_ttl_seconds: int = 604800
    session_cookie_secure: bool = False
    login_attempt_window_seconds: int = 900
    max_login_attempts: int = 5
    admin_email: str = "codexproject9@gmail.com"
    tavily_api_key: str = ""
    mistral_api_key: str = ""
    groq_api_key: str = ""


def get_settings() -> Settings:
    _load_dotenv_if_present()

    return Settings(
        smtp_email=os.getenv("SMTP_EMAIL", "codexproject9@gmail.com"),
        smtp_app_password=os.getenv("SMTP_APP_PASSWORD", ""),
        session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", "604800")),
        session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        login_attempt_window_seconds=int(os.getenv("LOGIN_ATTEMPT_WINDOW_SECONDS", "900")),
        max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
        admin_email=os.getenv("ADMIN_EMAIL", "codexproject9@gmail.com"),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        mistral_api_key=os.getenv("MISTRAL_API_KEY", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
    )


settings = get_settings()
