from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import create_engine
from sqlalchemy.engine import Engine


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
    command.upgrade(config, "head")
