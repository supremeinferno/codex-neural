import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_demo_app_runs_core_flows_without_provider_credentials(tmp_path):
    smoke_script = textwrap.dedent(
        """
        import fitz
        from fastapi.testclient import TestClient
        from backend.demo import app

        pdf = fitz.open()
        pdf.new_page().insert_text((72, 72), "Demo content")
        pdf_bytes = pdf.tobytes()
        pdf.close()

        with TestClient(app) as client:
            login = client.post(
                "/api/login",
                json={
                    "email": "codexproject9@gmail.com",
                    "password": "NexusDemo!2026",
                },
            )
            assert login.status_code == 200, login.text

            research = client.post(
                "/api/research",
                json={"topic": "sample topic"},
            )
            assert research.status_code == 200
            assert "placeholder" in research.json()["report"].lower()

            upload = client.post(
                "/api/individual/upload",
                files={"file": ("sample.pdf", pdf_bytes, "application/pdf")},
            )
            assert upload.status_code == 200, upload.text
            document_id = upload.json()["document_id"]

            answer = client.post(
                "/api/individual/chat",
                json={"question": "Summarize this file", "document_id": document_id},
            )
            assert answer.status_code == 200
            assert answer.json()["success"] is True

            viewer = client.get(f"/api/individual/{document_id}/file")
            assert viewer.status_code == 200
            assert viewer.headers["content-type"] == "application/pdf"

            dashboard = client.get("/api/admin/dashboard")
            assert dashboard.status_code == 200
            assert dashboard.json()["total_users"] == 1
        """
    )
    environment = os.environ.copy()
    for key in (
        "GROQ_API_KEY",
        "TAVILY_API_KEY",
        "MISTRAL_API_KEY",
        "SMTP_EMAIL",
        "SMTP_APP_PASSWORD",
        "REDIS_URL",
    ):
        environment.pop(key, None)
    environment["NEXUS_DEMO_DB_PATH"] = str(tmp_path / "demo.sqlite3")
    environment["NEXUS_DEMO_DOCUMENTS_DIR"] = str(tmp_path / "documents")

    result = subprocess.run(
        [sys.executable, "-c", smoke_script],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
