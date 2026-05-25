from __future__ import annotations

from pathlib import Path

from sqlalchemy.engine import Engine

from app.database import create_database_engine, run_migrations


class DatabaseService:
    @classmethod
    def create_engine(cls, database_path: str | Path) -> Engine:
        resolved_path = Path(database_path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        run_migrations(resolved_path)
        return create_database_engine(resolved_path)
