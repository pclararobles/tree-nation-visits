from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models import CustomerRecord, VisitRecord
from app.schemas import CustomerState, CustomerSummary, HourlyVisitCount, VisitEvent


class VisitService:
    @classmethod
    def record_visit_event(
        cls,
        event: VisitEvent,
        engine: Engine,
        visits_per_tree: int,
    ) -> CustomerState:
        return cls.record_visit(
            customer_id=event.customer_id,
            occurred_at=event.occurred_at or datetime.now(timezone.utc),
            engine=engine,
            visits_per_tree=visits_per_tree,
        )

    @classmethod
    def record_visit(
        cls,
        customer_id: str,
        occurred_at: datetime,
        engine: Engine,
        visits_per_tree: int,
    ) -> CustomerState:
        cls._validate_visits_per_tree(visits_per_tree)
        normalized_time = cls._normalize_datetime(occurred_at)
        occurred_at_text = normalized_time.isoformat()

        with Session(engine) as session:
            customer = cls._get_customer_by_external_id(session, customer_id)
            if customer is None:
                customer = CustomerRecord(
                    external_customer_id=customer_id,
                    visit_count=0,
                    trees_planted=0,
                    last_connection_at=occurred_at_text,
                )

            customer.visit_count += 1
            customer.trees_planted = customer.visit_count // visits_per_tree
            customer.last_connection_at = occurred_at_text

            session.add(customer)
            session.flush()
            session.add(VisitRecord(customer_id=customer.id, occurred_at=occurred_at_text))
            session.commit()
            session.refresh(customer)

        return cls._to_customer_state(customer)

    @classmethod
    def get_customer(
        cls,
        customer_id: str,
        engine: Engine,
    ) -> CustomerState | None:
        with Session(engine) as session:
            customer = cls._get_customer_by_external_id(session, customer_id)
            if customer is None:
                return None
            return cls._to_customer_state(customer)

    @classmethod
    def get_customer_summary(cls, engine: Engine) -> CustomerSummary:
        statement = select(CustomerRecord).order_by(
            CustomerRecord.visit_count.desc(),
            CustomerRecord.external_customer_id.asc(),
        )
        with Session(engine) as session:
            customers = [
                cls._to_customer_state(customer)
                for customer in session.exec(statement).all()
            ]

        return CustomerSummary(
            total_visits=sum(customer.visit_count for customer in customers),
            total_trees_planted=sum(customer.trees_planted for customer in customers),
            items=customers,
        )

    @classmethod
    def get_hourly_visit_counts(
        cls,
        engine: Engine,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[HourlyVisitCount]:
        start_text = None
        end_text = None
        if start is not None:
            start_text = cls._normalize_datetime(start).isoformat()
        if end is not None:
            end_text = cls._normalize_datetime(end).isoformat()

        hour = (func.substr(VisitRecord.occurred_at, 1, 13) + ":00:00+00:00").label(
            "hour"
        )
        statement = select(hour, func.count(VisitRecord.id)).select_from(VisitRecord)

        if start_text is not None:
            statement = statement.where(VisitRecord.occurred_at >= start_text)
        if end_text is not None:
            statement = statement.where(VisitRecord.occurred_at < end_text)

        statement = statement.group_by(hour).order_by(hour.asc())

        with Session(engine) as session:
            rows = session.execute(statement).all()

        return [
            HourlyVisitCount(
                hour=datetime.fromisoformat(row[0]),
                visit_count=row[1],
            )
            for row in rows
        ]

    @classmethod
    def _to_customer_state(cls, customer: CustomerRecord) -> CustomerState:
        return CustomerState(
            customer_id=customer.external_customer_id,
            visit_count=customer.visit_count,
            trees_planted=customer.trees_planted,
            last_connection_at=datetime.fromisoformat(customer.last_connection_at),
        )

    @classmethod
    def _get_customer_by_external_id(
        cls,
        session: Session,
        external_customer_id: str,
    ) -> CustomerRecord | None:
        statement = select(CustomerRecord).where(
            CustomerRecord.external_customer_id == external_customer_id
        )
        return session.exec(statement).one_or_none()

    @classmethod
    def _normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _validate_visits_per_tree(cls, visits_per_tree: int) -> None:
        if visits_per_tree < 1:
            raise ValueError("visits_per_tree must be greater than zero")
