from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api import admin_routes, auth_routes, individual_routes, research_routes
from backend.repositories import sqlite_repository


SESSION = {"id": 7, "email": "tester@example.com"}


def test_research_route_uses_injected_pipeline(monkeypatch):
    app = FastAPI()
    app.include_router(research_routes.router)
    app.dependency_overrides[research_routes.research_session] = lambda: SESSION
    app.dependency_overrides[research_routes.get_research_pipeline] = (
        lambda: lambda topic: {"topic": topic, "report": "local result"}
    )
    events = []
    monkeypatch.setattr(
        research_routes,
        "record_event",
        lambda **event: events.append(event),
    )

    response = TestClient(app).post("/api/research", json={"topic": "  local topic  "})

    assert response.status_code == 200
    assert response.json() == {"topic": "  local topic  ", "report": "local result"}
    assert events[0]["event_type"] == "research_requested"
    assert events[0]["user_id"] == SESSION["id"]


def test_main_app_starts_and_registers_feature_routers(monkeypatch):
    from backend import main

    monkeypatch.setattr(main, "initialize_admin_database", lambda: None)

    with TestClient(main.app) as client:
        response = client.get("/api/health")
        paths = main.app.openapi()["paths"]
        routes = {
            (path, method)
            for path, operations in paths.items()
            for method in operations
        }

    expected_routes = {
        ("/api", "get"),
        ("/api/register", "post"),
        ("/api/login", "post"),
        ("/api/forgot-password", "post"),
        ("/api/verify-otp", "post"),
        ("/api/reset-password", "post"),
        ("/api/research", "post"),
        ("/api/individual/upload", "post"),
        ("/api/individual/{document_id}/file", "get"),
        ("/api/individual/chat", "post"),
        ("/api/admin/dashboard", "get"),
        ("/api/admin/users/{user_id}", "delete"),
        ("/api/admin/logins/{activity_id}", "delete"),
        ("/api/admin/logins", "delete"),
        ("/api/health", "get"),
        ("/api/session", "get"),
        ("/api/logout", "post"),
    }

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert routes == expected_routes


def test_individual_upload_validates_and_passes_pdf_bytes(monkeypatch):
    app = FastAPI()
    app.include_router(individual_routes.router)
    app.dependency_overrides[individual_routes.document_upload_session] = lambda: SESSION
    received = {}

    def index_document(pdf_bytes, filename):
        received["pdf_bytes"] = pdf_bytes
        received["filename"] = filename
        return {"success": True, "document_id": "doc-1"}

    app.dependency_overrides[individual_routes.get_document_indexer] = lambda: index_document
    monkeypatch.setattr(individual_routes, "record_event", lambda **event: None)
    client = TestClient(app)

    rejected = client.post(
        "/api/individual/upload",
        files={"file": ("notes.txt", b"not a PDF", "text/plain")},
    )
    accepted = client.post(
        "/api/individual/upload",
        files={"file": ("notes.pdf", b"%PDF-test", "application/pdf")},
    )

    assert rejected.status_code == 200
    assert rejected.json()["success"] is False
    assert accepted.json() == {"success": True, "document_id": "doc-1"}
    assert received == {"pdf_bytes": b"%PDF-test", "filename": "notes.pdf"}


def test_individual_chat_strips_question_and_uses_injected_answerer(monkeypatch):
    app = FastAPI()
    app.include_router(individual_routes.router)
    app.dependency_overrides[individual_routes.document_chat_session] = lambda: SESSION
    received = {}

    def answer_question(question, document_id):
        received["question"] = question
        received["document_id"] = document_id
        return {"success": True, "answer": "local answer"}

    app.dependency_overrides[individual_routes.get_document_answerer] = lambda: answer_question
    monkeypatch.setattr(individual_routes, "record_event", lambda **event: None)

    response = TestClient(app).post(
        "/api/individual/chat",
        json={"question": "  what changed?  ", "document_id": "doc-1"},
    )

    assert response.status_code == 200
    assert response.json() == {"success": True, "answer": "local answer"}
    assert received == {"question": "what changed?", "document_id": "doc-1"}


def test_individual_pdf_route_supports_inline_and_download(tmp_path):
    pdf_path = tmp_path / "a1b2c3d4e5f6.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    app = FastAPI()
    app.include_router(individual_routes.router)
    app.dependency_overrides[individual_routes.document_chat_session] = lambda: SESSION
    app.dependency_overrides[individual_routes.get_document_pdf_resolver] = (
        lambda: lambda document_id: str(pdf_path)
        if document_id == "a1b2c3d4e5f6"
        else None
    )
    client = TestClient(app)

    inline = client.get("/api/individual/a1b2c3d4e5f6/file")
    download = client.get("/api/individual/a1b2c3d4e5f6/file?download=true")
    invalid = client.get("/api/individual/not-valid/file")

    assert inline.status_code == 200
    assert inline.headers["content-type"] == "application/pdf"
    assert inline.headers["content-disposition"].startswith("inline;")
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.content == b"%PDF-test"
    assert invalid.status_code == 400


def test_successful_login_records_login_activity(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_repository, "DB_PATH", tmp_path / "login_test.db")
    sqlite_repository.initialize_admin_database()
    monkeypatch.setattr(auth_routes, "is_login_attempt_allowed", lambda *args: True)
    monkeypatch.setattr(
        auth_routes,
        "authenticate_user",
        lambda email, password: {"id": 4, "email": email, "role": "user"},
    )
    monkeypatch.setattr(auth_routes, "clear_login_attempts", lambda *args: None)
    monkeypatch.setattr(auth_routes, "create_session", lambda *args: ("test-session", 9999999999))
    monkeypatch.setattr(auth_routes, "record_event", lambda **event: None)

    app = FastAPI()
    app.include_router(auth_routes.router)
    response = TestClient(app).post(
        "/api/login",
        json={"email": "user@example.com", "password": "StrongPass!123"},
    )

    conn = sqlite_repository.get_db()
    login = conn.execute(
        "SELECT user_id, email, login_time FROM login_activity"
    ).fetchone()
    conn.close()

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.cookies.get(auth_routes.SESSION_COOKIE_NAME) == "test-session"
    assert login["user_id"] == 4
    assert login["email"] == "user@example.com"
    assert login["login_time"]


def test_admin_routes_use_repository_and_protect_admin_role(tmp_path, monkeypatch):
    monkeypatch.setattr(sqlite_repository, "DB_PATH", tmp_path / "admin_test.db")
    sqlite_repository.initialize_admin_database()
    conn = sqlite_repository.get_db()
    conn.execute(
        "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
        ("user@example.com", "unused", "user"),
    )
    conn.execute(
        "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
        ("admin@example.com", "unused", "admin"),
    )
    conn.commit()
    conn.close()

    app = FastAPI()
    app.include_router(admin_routes.router)
    app.dependency_overrides[admin_routes.verify_admin] = lambda: SESSION
    monkeypatch.setattr(admin_routes, "record_event", lambda **event: None)
    client = TestClient(app)

    dashboard = client.get("/api/admin/dashboard")
    blocked = client.delete("/api/admin/users/2")
    deleted = client.delete("/api/admin/users/1")

    assert dashboard.status_code == 200
    assert dashboard.json()["total_users"] == 2
    assert blocked.status_code == 403
    assert deleted.status_code == 200
    conn = sqlite_repository.get_db()
    remaining = conn.execute("SELECT email FROM users ORDER BY id").fetchall()
    conn.close()
    assert [row["email"] for row in remaining] == ["admin@example.com"]
