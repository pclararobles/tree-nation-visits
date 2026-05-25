from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.engine import Engine

from app.schemas import CustomerState, CustomerSummary, HourlyVisitCounts, VisitEvent
from app.services.visit_service import VisitService


router = APIRouter(prefix="/api")


def get_database_engine(request: Request) -> Engine:
    return request.app.state.database_engine


def get_visits_per_tree(request: Request) -> int:
    return request.app.state.visits_per_tree


@router.post(
    "/visits",
    response_model=CustomerState,
    status_code=status.HTTP_201_CREATED,
    tags=["visits"],
)
def receive_visit(
    event: VisitEvent,
    engine: Engine = Depends(get_database_engine),
    visits_per_tree: int = Depends(get_visits_per_tree),
) -> CustomerState:
    return VisitService.record_visit_event(event, engine, visits_per_tree)


@router.get(
    "/customers",
    response_model=CustomerSummary,
    tags=["customers"],
)
def list_customers(
    engine: Engine = Depends(get_database_engine),
) -> CustomerSummary:
    return VisitService.get_customer_summary(engine)


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerState,
    tags=["customers"],
)
def get_customer(
    customer_id: str,
    engine: Engine = Depends(get_database_engine),
) -> CustomerState:
    customer = VisitService.get_customer(customer_id, engine)
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    return customer


@router.get(
    "/visits/hourly",
    response_model=HourlyVisitCounts,
    tags=["visits"],
)
def get_hourly_visits(
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    engine: Engine = Depends(get_database_engine),
) -> HourlyVisitCounts:
    return HourlyVisitCounts(
        items=VisitService.get_hourly_visit_counts(engine, start, end)
    )
