from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel

from backend.auth import record_event, require_permissions

router = APIRouter()
document_upload_session = require_permissions("document_upload")
document_chat_session = require_permissions("document_chat")


class IndividualQuestionRequest(BaseModel):
    question: str
    document_id: str


def get_document_indexer() -> Callable[[bytes, str], dict]:
    from backend.individual import build_individual_index

    return build_individual_index


def get_document_answerer() -> Callable[[str, str], dict]:
    from backend.individual import answer_individual_question

    return answer_individual_question


@router.post("/api/individual/upload")
async def upload_individual_pdf(
    file: UploadFile = File(...),
    session: dict = Depends(document_upload_session),
    index_document: Callable[[bytes, str], dict] = Depends(get_document_indexer),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"success": False, "message": "Only PDF files are allowed."}

    pdf_bytes = await file.read()
    record_event(
        event_type="pdf_upload",
        path="/api/individual/upload",
        details={"filename": file.filename, "size_bytes": len(pdf_bytes)},
        user_id=session["id"],
        email=session["email"],
    )
    return index_document(pdf_bytes, file.filename)


@router.post("/api/individual/chat")
def individual_chat(
    request: IndividualQuestionRequest,
    session: dict = Depends(document_chat_session),
    answer_question: Callable[[str, str], dict] = Depends(get_document_answerer),
):
    question = request.question.strip()
    if not question:
        return {"success": False, "message": "Please enter a question."}

    record_event(
        event_type="document_chat",
        path="/api/individual/chat",
        details={
            "document_id": request.document_id,
            "question_length": len(question),
        },
        user_id=session["id"],
        email=session["email"],
    )
    return answer_question(question, request.document_id)
