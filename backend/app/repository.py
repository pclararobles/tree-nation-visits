from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.database import CustomerRecord, VisitRecord


@dataclass(frozen=True)
class VisitRepository:
    engine: Engine

    @contextmanager
    def session(self) -> Iterator[Session]:
        with Session(self.engine) as session:
            yield session

    def get_customer_record(
        self,
        session: Session,
        customer_id: str,
    ) -> CustomerRecord | None:
        return session.get(CustomerRecord, customer_id)

    def save_customer_visit(
        self,
        session: Session,
        customer: CustomerRecord,
        visit: VisitRecord,
    ) -> CustomerRecord:
        session.add(customer)
        session.add(visit)
        session.commit()
        session.refresh(customer)
        return customer

    def get_customer_record_by_id(self, customer_id: str) -> CustomerRecord | None:
        with self.session() as session:
            return session.get(CustomerRecord, customer_id)

    def list_customer_records(self) -> list[CustomerRecord]:
        statement = select(CustomerRecord).order_by(
            CustomerRecord.visit_count.desc(),
            CustomerRecord.customer_id.asc(),
        )

        with self.session() as session:
            return list(session.exec(statement).all())

    def hourly_visit_rows(
        self,
        start: str | None = None,
        end: str | None = None,
    ) -> list[tuple[str, int]]:
        hour = (func.substr(VisitRecord.occurred_at, 1, 13) + ":00:00+00:00").label(
            "hour"
        )
        statement = select(hour, func.count(VisitRecord.id)).select_from(VisitRecord)

        if start is not None:
            statement = statement.where(VisitRecord.occurred_at >= start)
        if end is not None:
            statement = statement.where(VisitRecord.occurred_at < end)

        statement = statement.group_by(hour).order_by(hour.asc())

        with self.session() as session:
            return [(row[0], row[1]) for row in session.execute(statement).all()]
