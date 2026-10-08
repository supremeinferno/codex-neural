from datetime import datetime

from fastapi import APIRouter

from backend.repositories.sqlite_repository import DB_PATH

router = APIRouter()


@router.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "database": DB_PATH.name,
        "timestamp": datetime.now().isoformat(sep=" ", timespec="seconds"),
    }
