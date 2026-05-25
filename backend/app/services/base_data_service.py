from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models import CustomerRecord
from app.services.visit_service import VisitService


BASE_CUSTOMER_VISIT_COUNTS = tuple(
    (f"customer-{customer_number:03d}", customer_number)
    for customer_number in range(1, 11)
)
BASE_DATA_START = datetime(2026, 5, 25, 9, 0, tzinfo=timezone.utc)


class BaseDataService:
    @classmethod
    def seed_base_customer_data(cls, engine: Engine, visits_per_tree: int) -> None:
        existing_customer_ids = cls._get_existing_base_customer_ids(engine)

        for customer_index, (customer_id, visit_count) in enumerate(
            BASE_CUSTOMER_VISIT_COUNTS
        ):
            if customer_id in existing_customer_ids:
                continue

            for visit_index in range(visit_count):
                VisitService.record_visit(
                    customer_id=customer_id,
                    occurred_at=BASE_DATA_START
                    + timedelta(minutes=(customer_index * 20) + visit_index),
                    engine=engine,
                    visits_per_tree=visits_per_tree,
                )

    @classmethod
    def _get_existing_base_customer_ids(cls, engine: Engine) -> set[str]:
        base_customer_ids = [
            customer_id for customer_id, _ in BASE_CUSTOMER_VISIT_COUNTS
        ]
        statement = select(CustomerRecord.external_customer_id).where(
            CustomerRecord.external_customer_id.in_(base_customer_ids)
        )

        with Session(engine) as session:
            return set(session.exec(statement).all())
