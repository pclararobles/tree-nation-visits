from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.database import (
    CustomerRecord,
    VisitRecord,
    create_database_engine,
    run_migrations,
)
from app.models import CustomerState, CustomerSummary, HourlyVisitCount


@dataclass
class VisitRepository:
    database_path: Path
    visits_per_tree: int
    engine: Engine = field(init=False)

    def __post_init__(self) -> None:
        if self.visits_per_tree < 1:
            raise ValueError("visits_per_tree must be greater than zero")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        run_migrations(self.database_path)
        self.engine = create_database_engine(self.database_path)

    def record_visit(self, customer_id: str, occurred_at: datetime) -> CustomerState:
        normalized_time = self._normalize_datetime(occurred_at)
        occurred_at_text = self._serialize_datetime(normalized_time)

        with Session(self.engine) as session:
            customer = session.get(CustomerRecord, customer_id)
            if customer is None:
                customer = CustomerRecord(
                    customer_id=customer_id,
                    visit_count=0,
                    trees_planted=0,
                    last_connection_at=occurred_at_text,
                )

            customer.visit_count += 1
            customer.trees_planted = customer.visit_count // self.visits_per_tree
            customer.last_connection_at = occurred_at_text

            session.add(customer)
            session.add(
                VisitRecord(
                    customer_id=customer_id,
                    occurred_at=occurred_at_text,
                )
            )
            session.commit()
            session.refresh(customer)

            return self._to_customer_state(customer)

    def get_customer(self, customer_id: str) -> CustomerState | None:
        with Session(self.engine) as session:
            customer = session.get(CustomerRecord, customer_id)
            if customer is None:
                return None
            return self._to_customer_state(customer)

    def customer_summary(self) -> CustomerSummary:
        customers = self.list_customers()
        return CustomerSummary(
            total_visits=sum(customer.visit_count for customer in customers),
            total_trees_planted=sum(customer.trees_planted for customer in customers),
            items=customers,
        )

    def list_customers(self) -> list[CustomerState]:
        statement = select(CustomerRecord).order_by(
            CustomerRecord.visit_count.desc(),
            CustomerRecord.customer_id.asc(),
        )

        with Session(self.engine) as session:
            customers = session.exec(statement).all()

        return [self._to_customer_state(customer) for customer in customers]

    def hourly_visit_counts(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[HourlyVisitCount]:
        hour = (func.substr(VisitRecord.occurred_at, 1, 13) + ":00:00+00:00").label(
            "hour"
        )
        statement = select(hour, func.count(VisitRecord.id)).select_from(VisitRecord)

        if start is not None:
            statement = statement.where(
                VisitRecord.occurred_at
                >= self._serialize_datetime(self._normalize_datetime(start))
            )
        if end is not None:
            statement = statement.where(
                VisitRecord.occurred_at
                < self._serialize_datetime(self._normalize_datetime(end))
            )

        statement = statement.group_by(hour).order_by(hour.asc())

        with Session(self.engine) as session:
            rows = session.execute(statement).all()

        return [
            HourlyVisitCount(
                hour=datetime.fromisoformat(row[0]),
                visit_count=row[1],
            )
            for row in rows
        ]

    @staticmethod
    def _to_customer_state(customer: CustomerRecord) -> CustomerState:
        return CustomerState(
            customer_id=customer.customer_id,
            visit_count=customer.visit_count,
            trees_planted=customer.trees_planted,
            last_connection_at=datetime.fromisoformat(customer.last_connection_at),
        )

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _serialize_datetime(value: datetime) -> str:
        return value.isoformat()
