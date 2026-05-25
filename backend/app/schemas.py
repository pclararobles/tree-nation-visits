from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, Field, field_serializer, field_validator


CustomerId = Annotated[str, Field(min_length=1, max_length=128)]


class VisitEvent(BaseModel):
    customer_id: CustomerId
    occurred_at: datetime | None = None

    @field_validator("occurred_at")
    @classmethod
    def normalize_occurred_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class CustomerState(BaseModel):
    customer_id: str
    visit_count: int
    trees_planted: int
    last_connection_at: datetime

    @field_serializer("last_connection_at")
    def serialize_last_connection_at(self, value: datetime) -> str:
        return value.isoformat()


class CustomerSummary(BaseModel):
    total_visits: int
    total_trees_planted: int
    items: list[CustomerState]


class HourlyVisitCount(BaseModel):
    hour: datetime
    visit_count: int

    @field_serializer("hour")
    def serialize_hour(self, value: datetime) -> str:
        return value.isoformat()


class HourlyVisitCounts(BaseModel):
    items: list[HourlyVisitCount]
