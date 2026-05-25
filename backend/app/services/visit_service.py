from __future__ import annotations

from datetime import datetime, timezone

from app.database import CustomerRecord, VisitRecord
from app.models import CustomerState, CustomerSummary, HourlyVisitCount, VisitEvent
from app.repository import VisitRepository


class VisitService:
    @classmethod
    def record_visit_event(
        cls,
        event: VisitEvent,
        repository: VisitRepository,
        visits_per_tree: int,
    ) -> CustomerState:
        return cls.record_visit(
            customer_id=event.customer_id,
            occurred_at=event.occurred_at or datetime.now(timezone.utc),
            repository=repository,
            visits_per_tree=visits_per_tree,
        )

    @classmethod
    def record_visit(
        cls,
        customer_id: str,
        occurred_at: datetime,
        repository: VisitRepository,
        visits_per_tree: int,
    ) -> CustomerState:
        cls._validate_visits_per_tree(visits_per_tree)
        normalized_time = cls._normalize_datetime(occurred_at)
        occurred_at_text = normalized_time.isoformat()

        with repository.session() as session:
            customer = repository.get_customer_record(session, customer_id)
            if customer is None:
                customer = CustomerRecord(
                    customer_id=customer_id,
                    visit_count=0,
                    trees_planted=0,
                    last_connection_at=occurred_at_text,
                )

            customer.visit_count += 1
            customer.trees_planted = customer.visit_count // visits_per_tree
            customer.last_connection_at = occurred_at_text

            customer = repository.save_customer_visit(
                session=session,
                customer=customer,
                visit=VisitRecord(
                    customer_id=customer_id,
                    occurred_at=occurred_at_text,
                ),
            )

        return cls._to_customer_state(customer)

    @classmethod
    def get_customer(
        cls,
        customer_id: str,
        repository: VisitRepository,
    ) -> CustomerState | None:
        customer = repository.get_customer_record_by_id(customer_id)
        if customer is None:
            return None
        return cls._to_customer_state(customer)

    @classmethod
    def customer_summary(cls, repository: VisitRepository) -> CustomerSummary:
        customers = [
            cls._to_customer_state(customer)
            for customer in repository.list_customer_records()
        ]
        return CustomerSummary(
            total_visits=sum(customer.visit_count for customer in customers),
            total_trees_planted=sum(customer.trees_planted for customer in customers),
            items=customers,
        )

    @classmethod
    def hourly_visit_counts(
        cls,
        repository: VisitRepository,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[HourlyVisitCount]:
        start_text = None
        end_text = None
        if start is not None:
            start_text = cls._normalize_datetime(start).isoformat()
        if end is not None:
            end_text = cls._normalize_datetime(end).isoformat()

        return [
            HourlyVisitCount(
                hour=datetime.fromisoformat(hour),
                visit_count=visit_count,
            )
            for hour, visit_count in repository.hourly_visit_rows(
                start_text,
                end_text,
            )
        ]

    @classmethod
    def _to_customer_state(cls, customer: CustomerRecord) -> CustomerState:
        return CustomerState(
            customer_id=customer.customer_id,
            visit_count=customer.visit_count,
            trees_planted=customer.trees_planted,
            last_connection_at=datetime.fromisoformat(customer.last_connection_at),
        )

    @classmethod
    def _normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _validate_visits_per_tree(cls, visits_per_tree: int) -> None:
        if visits_per_tree < 1:
            raise ValueError("visits_per_tree must be greater than zero")
