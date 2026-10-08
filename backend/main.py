import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.admin_routes import router as admin_router
from backend.api.auth_routes import router as auth_router
from backend.api.health_routes import router as health_router
from backend.api.individual_routes import router as individual_router
from backend.api.research_routes import router as research_router
from backend.middleware.rate_limit import install_rate_limit_middleware
from backend.repositories.sqlite_repository import initialize_admin_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_admin_database()
    yield


app = FastAPI(
    title="Nexus Research API",
    description="Multi-Agent AI Research System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "FRONTEND_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(research_router)
app.include_router(individual_router)
app.include_router(admin_router)
app.include_router(health_router)

install_rate_limit_middleware(app)
