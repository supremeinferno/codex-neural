"""Local UI demo using deterministic services and an isolated SQLite database."""

from __future__ import annotations

import hashlib
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

DEMO_DB_PATH = Path(
    os.getenv(
        "NEXUS_DEMO_DB_PATH",
        str(Path(tempfile.gettempdir()) / "nexus-research-demo.sqlite3"),
    )
)
os.environ["NEXUS_DB_PATH"] = str(DEMO_DB_PATH)

from backend.api import individual_routes, research_routes
from backend.middleware import rate_limit
from backend.repositories import sqlite_repository
from backend.services.auth_service import register_user
from backend.main import app

DEMO_EMAIL = "codexproject9@gmail.com"
DEMO_PASSWORD = "NexusDemo!2026"
DEMO_DOCUMENTS_DIR = Path(
    os.getenv(
        "NEXUS_DEMO_DOCUMENTS_DIR",
        str(DEMO_DB_PATH.parent / "nexus-research-demo-pdfs"),
    )
)


def demo_research_pipeline(topic: str) -> dict:
    return {
        "report": (
            f"# Local demo report: {topic}\n\n"
            "> Placeholder response. No search provider or language model was called.\n\n"
            "## Overview\n\n"
            f"This sample report demonstrates how a completed research response appears for **{topic}**. "
            "In live mode, Nexus gathers web sources and asks its configured model to synthesize a report.\n\n"
            "## Example findings\n\n"
            "- This content is deterministic demonstration text, not sourced research.\n"
            "- The UI, session flow, request handling, and report rendering are running normally.\n\n"
            "## Sources\n\n"
            "No external sources were requested in local demo mode."
        )
    }


def demo_index_document(pdf_bytes: bytes, document_name: str) -> dict:
    DEMO_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    document_id = hashlib.sha256(pdf_bytes).hexdigest()[:12]
    pdf_path = DEMO_DOCUMENTS_DIR / f"{document_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)
    return {
        "success": True,
        "message": "PDF accepted in placeholder mode; no embeddings were created.",
        "document_id": document_id,
        "document_name": document_name,
        "pages": 1,
        "chunks": 1,
    }


def demo_answer_question(question: str, document_id: str) -> dict:
    if not demo_pdf_path(document_id):
        return {"success": False, "message": "Demo document was not found."}
    return {
        "success": True,
        "answer": (
            f"This is a placeholder answer to: **{question}**\n\n"
            "The demo validates the chat workflow, but it does not read or interpret the PDF. "
            "Configure the live embedding and model providers for document-grounded answers."
        ),
        "sources": [{"page": 1, "section": "Demo placeholder"}],
    }


def demo_pdf_path(document_id: str) -> str | None:
    if len(document_id) != 12 or any(char not in "0123456789abcdef" for char in document_id):
        return None
    path = DEMO_DOCUMENTS_DIR / f"{document_id}.pdf"
    return str(path) if path.is_file() else None


app.dependency_overrides[research_routes.get_research_pipeline] = (
    lambda: demo_research_pipeline
)
app.dependency_overrides[individual_routes.get_document_indexer] = (
    lambda: demo_index_document
)
app.dependency_overrides[individual_routes.get_document_answerer] = (
    lambda: demo_answer_question
)
app.dependency_overrides[individual_routes.get_document_pdf_resolver] = (
    lambda: demo_pdf_path
)
rate_limit.RATE_LIMIT_USE_REDIS = False

_base_lifespan = app.router.lifespan_context


@asynccontextmanager
async def demo_lifespan(application):
    async with _base_lifespan(application):
        if not sqlite_repository.get_user_by_email(DEMO_EMAIL):
            created, message = register_user(
                DEMO_EMAIL,
                DEMO_PASSWORD,
                role="admin",
            )
            if not created:
                raise RuntimeError(f"Unable to initialize demo account: {message}")
        yield


app.router.lifespan_context = demo_lifespan