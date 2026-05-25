from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.models import CustomerState, HourlyVisitCount


@dataclass(frozen=True)
class VisitRepository:
    database_path: Path
    visits_per_tree: int

    def __post_init__(self) -> None:
        if self.visits_per_tree < 1:
            raise ValueError("visits_per_tree must be greater than zero")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    visit_count INTEGER NOT NULL,
                    trees_planted INTEGER NOT NULL,
                    last_connection_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_visits_occurred_at
                ON visits(occurred_at)
                """
            )

    def record_visit(self, customer_id: str, occurred_at: datetime) -> CustomerState:
        normalized_time = self._normalize_datetime(occurred_at)
        occurred_at_text = self._serialize_datetime(normalized_time)

        with self._connect() as connection:
            connection.execute(
                "INSERT INTO visits (customer_id, occurred_at) VALUES (?, ?)",
                (customer_id, occurred_at_text),
            )
            existing = connection.execute(
                """
                SELECT visit_count
                FROM customers
                WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()

            visit_count = (existing["visit_count"] if existing else 0) + 1
            trees_planted = visit_count // self.visits_per_tree

            connection.execute(
                """
                INSERT INTO customers (
                    customer_id,
                    visit_count,
                    trees_planted,
                    last_connection_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET
                    visit_count = excluded.visit_count,
                    trees_planted = excluded.trees_planted,
                    last_connection_at = excluded.last_connection_at
                """,
                (customer_id, visit_count, trees_planted, occurred_at_text),
            )

        return CustomerState(
            customer_id=customer_id,
            visit_count=visit_count,
            trees_planted=trees_planted,
            last_connection_at=normalized_time,
        )

    def get_customer(self, customer_id: str) -> CustomerState | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT customer_id, visit_count, trees_planted, last_connection_at
                FROM customers
                WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()

        if row is None:
            return None

        return CustomerState(
            customer_id=row["customer_id"],
            visit_count=row["visit_count"],
            trees_planted=row["trees_planted"],
            last_connection_at=datetime.fromisoformat(row["last_connection_at"]),
        )

    def hourly_visit_counts(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[HourlyVisitCount]:
        query = [
            """
            SELECT
                substr(occurred_at, 1, 13) || ':00:00+00:00' AS hour,
                COUNT(*) AS visit_count
            FROM visits
            """
        ]
        parameters: list[str] = []
        filters: list[str] = []

        if start is not None:
            filters.append("occurred_at >= ?")
            parameters.append(self._serialize_datetime(self._normalize_datetime(start)))
        if end is not None:
            filters.append("occurred_at < ?")
            parameters.append(self._serialize_datetime(self._normalize_datetime(end)))
        if filters:
            query.append("WHERE " + " AND ".join(filters))

        query.append(
            """
            GROUP BY hour
            ORDER BY hour ASC
            """
        )

        with self._connect() as connection:
            rows = connection.execute("\n".join(query), parameters).fetchall()

        return [
            HourlyVisitCount(
                hour=datetime.fromisoformat(row["hour"]),
                visit_count=row["visit_count"],
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _serialize_datetime(value: datetime) -> str:
        return value.replace(microsecond=0).isoformat()
