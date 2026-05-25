from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Field, SQLModel, create_engine
from sqlalchemy.engine import Engine


BASELINE_REVISION = "0001_create_visit_tables"


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


def database_url(database_path: Path) -> str:
    return f"sqlite:///{database_path}"


def create_database_engine(database_path: Path) -> Engine:
    return create_engine(
        database_url(database_path),
        connect_args={"check_same_thread": False},
    )


def run_migrations(database_path: Path) -> None:
    config = Config()
    config.set_main_option(
        "script_location",
        str(Path(__file__).parent / "migrations"),
    )
    config.set_main_option("sqlalchemy.url", database_url(database_path))
    if _has_legacy_schema_without_version(database_path):
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")


def _has_legacy_schema_without_version(database_path: Path) -> bool:
    if not database_path.exists():
        return False

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    return "alembic_version" not in tables and {"customers", "visits"}.issubset(tables)
