from __future__ import annotations

from sqlmodel import Field, SQLModel


class CustomerRecord(SQLModel, table=True):
    __tablename__ = "customers"

    customer_id: str = Field(primary_key=True, max_length=128)
    visit_count: int = Field(nullable=False)
    trees_planted: int = Field(nullable=False)
    last_connection_at: str = Field(nullable=False)


class VisitRecord(SQLModel, table=True):
    __tablename__ = "visits"

    id: int | None = Field(default=None, primary_key=True)
    customer_id: str = Field(foreign_key="customers.customer_id", nullable=False)
    occurred_at: str = Field(nullable=False)
