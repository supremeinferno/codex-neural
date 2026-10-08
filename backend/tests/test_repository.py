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
