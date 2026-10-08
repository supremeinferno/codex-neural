import sqlite3

from backend.repositories import sqlite_repository


def test_repository_initializes_database_for_new_app_state(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_repository, "DB_PATH", tmp_path / "repo_test.db")

    sqlite_repository.initialize_admin_database()

    conn = sqlite_repository.get_db()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {row[0] for row in tables}

    assert "users" in names
    assert "login_activity" in names
    conn.close()


def test_repository_migrates_legacy_users_without_losing_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    monkeypatch.setattr(sqlite_repository, "DB_PATH", db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, password TEXT)"
    )
    conn.execute(
        "INSERT INTO users (id, email, password) VALUES (?, ?, ?)",
        (1, "admin@localhost", "legacy-hash"),
    )
    conn.commit()
    conn.close()

    sqlite_repository.initialize_admin_database()

    conn = sqlite_repository.get_db()
    user = conn.execute(
        "SELECT id, email, password, role, created_at FROM users WHERE id = 1"
    ).fetchone()
    conn.close()

    assert user["email"] == "admin@localhost"
    assert user["password"] == "legacy-hash"
    assert user["role"] == "admin"
    assert user["created_at"]
