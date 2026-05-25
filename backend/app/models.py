from __future__ import annotations

from sqlmodel import Field, SQLModel


class CustomerRecord(SQLModel, table=True):
    __tablename__ = "customers"

    id: int | None = Field(default=None, primary_key=True)
    external_customer_id: str = Field(max_length=128, unique=True, index=True)
    visit_count: int = Field(nullable=False)
    trees_planted: int = Field(nullable=False)
    last_connection_at: str = Field(nullable=False)


class VisitRecord(SQLModel, table=True):
    __tablename__ = "visits"

    id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customers.id", nullable=False)
    occurred_at: str = Field(nullable=False)
