from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.models import CustomerState, HourlyVisitCounts, VisitEvent
from app.repository import VisitRepository


DEFAULT_DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/visits.db"))
DEFAULT_VISITS_PER_TREE = int(os.getenv("VISITS_PER_TREE", "5"))
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def create_app(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    visits_per_tree: int = DEFAULT_VISITS_PER_TREE,
    allowed_origins: list[str] | None = None,
) -> FastAPI:
    repository = VisitRepository(Path(database_path), visits_per_tree)
    app = FastAPI(
        title="Tree Nation Visit Tracker",
        version="0.1.0",
        description="Tracks shop visits and converts configurable visit milestones into planted tree counters.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or DEFAULT_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_repository() -> VisitRepository:
        return repository

    @app.post(
        "/api/visits",
        response_model=CustomerState,
        status_code=status.HTTP_201_CREATED,
        tags=["visits"],
    )
    def receive_visit(
        event: VisitEvent,
        repo: VisitRepository = Depends(get_repository),
    ) -> CustomerState:
        occurred_at = event.occurred_at or datetime.now(timezone.utc)
        return repo.record_visit(event.customer_id, occurred_at)

    @app.get(
        "/api/customers/{customer_id}",
        response_model=CustomerState,
        tags=["customers"],
    )
    def get_customer(
        customer_id: str,
        repo: VisitRepository = Depends(get_repository),
    ) -> CustomerState:
        customer = repo.get_customer(customer_id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        return customer

    @app.get(
        "/api/visits/hourly",
        response_model=HourlyVisitCounts,
        tags=["visits"],
    )
    def get_hourly_visits(
        start: datetime | None = Query(default=None),
        end: datetime | None = Query(default=None),
        repo: VisitRepository = Depends(get_repository),
    ) -> HourlyVisitCounts:
        return HourlyVisitCounts(items=repo.hourly_visit_counts(start, end))

    return app


app = create_app()
