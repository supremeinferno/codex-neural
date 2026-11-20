import atexit
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


_test_data = tempfile.TemporaryDirectory(prefix="codex-backend-tests-")
_test_database = Path(_test_data.name, "users.db").resolve()
_repository_database = Path(__file__).resolve().parents[2] / "backend" / "users.db"
if _test_database == _repository_database.resolve():
    raise RuntimeError("Backend tests must not use the repository database.")
os.environ["CODEX_DATABASE_PATH"] = str(_test_database)
os.environ["GROQ_API_KEY"] = "test-groq-key"
os.environ["TAVILY_API_KEY"] = "test-tavily-key"
os.environ["MISTRAL_API_KEY"] = "test-mistral-key"
atexit.register(_test_data.cleanup)


@pytest.fixture
def app_module():
    from backend import main

    return main


@pytest.fixture(autouse=True)
def clear_test_database(app_module):
    conn = app_module.get_db()
    for table in (
        "conversation_messages",
        "conversations",
        "user_documents",
        "login_activity",
        "password_reset_otps",
        "auth_sessions",
        "users",
    ):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


@pytest.fixture
def client(app_module):
    with TestClient(app_module.app) as test_client:
        yield test_client


@pytest.fixture
def user_factory(app_module):
    def create_user(email):
        from backend import auth

        created, message = auth.register_user(email, "test-password")
        assert created, message

        conn = app_module.get_db()
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
        conn.close()
        token = auth.create_session(row["id"])
        return {"Authorization": f"Bearer {token}"}, row["id"]

    return create_user
