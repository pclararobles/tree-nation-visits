from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.models import CustomerState, CustomerSummary, HourlyVisitCounts, VisitEvent
from app.repository import VisitRepository
from app.services.visit_service import VisitService


router = APIRouter(prefix="/api")


def get_visit_repository(request: Request) -> VisitRepository:
    return request.app.state.visit_repository


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
    repository: VisitRepository = Depends(get_visit_repository),
    visits_per_tree: int = Depends(get_visits_per_tree),
) -> CustomerState:
    return VisitService.record_visit_event(event, repository, visits_per_tree)


@router.get(
    "/customers",
    response_model=CustomerSummary,
    tags=["customers"],
)
def list_customers(
    repository: VisitRepository = Depends(get_visit_repository),
) -> CustomerSummary:
    return VisitService.customer_summary(repository)


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerState,
    tags=["customers"],
)
def get_customer(
    customer_id: str,
    repository: VisitRepository = Depends(get_visit_repository),
) -> CustomerState:
    customer = VisitService.get_customer(customer_id, repository)
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
    repository: VisitRepository = Depends(get_visit_repository),
) -> HourlyVisitCounts:
    return HourlyVisitCounts(
        items=VisitService.hourly_visit_counts(repository, start, end)
    )
