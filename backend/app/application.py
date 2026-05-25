from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    DEFAULT_ALLOWED_ORIGINS,
    DEFAULT_DATABASE_PATH,
    DEFAULT_VISITS_PER_TREE,
)
from app.repository import VisitRepository
from app.services.database_service import DatabaseService
from app.view import router


def create_app(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    visits_per_tree: int = DEFAULT_VISITS_PER_TREE,
    allowed_origins: list[str] | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Tree Nation Visit Tracker",
        version="0.1.0",
        description="Tracks shop visits and converts configurable visit milestones into planted tree counters.",
    )
    engine = DatabaseService.create_engine(database_path)
    app.state.visit_repository = VisitRepository(engine)
    app.state.visits_per_tree = visits_per_tree

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or DEFAULT_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    return app
