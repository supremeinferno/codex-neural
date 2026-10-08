from __future__ import annotations

from typing import Callable

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth import record_event, require_permissions

router = APIRouter()
research_session = require_permissions("research")


class ResearchRequest(BaseModel):
    topic: str


def get_research_pipeline() -> Callable[[str], dict]:
    from backend.pipeline import run_research_pipeline

    return run_research_pipeline


@router.post("/api/research")
def research(
    request: ResearchRequest,
    session: dict = Depends(research_session),
    run_pipeline: Callable[[str], dict] = Depends(get_research_pipeline),
):
    record_event(
        event_type="research_requested",
        path="/api/research",
        details={"topic": request.topic[:500]},
        user_id=session["id"],
        email=session["email"],
    )
    return run_pipeline(request.topic)
