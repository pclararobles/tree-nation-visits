import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import create_app


def test_app_initialization_runs_database_migrations(tmp_path):
    database_path = tmp_path / "visits.db"

    create_app(database_path=database_path, visits_per_tree=5)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        version = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()

    assert {"alembic_version", "customers", "visits"}.issubset(tables)
    assert version == ("0001_create_visit_tables",)


def test_app_reuses_singleton_repository_dependency(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=5)
    client = TestClient(app)
    repository = app.state.visit_repository

    response = client.post("/api/visits", json={"customer_id": "customer-123"})

    assert response.status_code == 201
    assert app.state.visit_repository is repository


def test_visit_events_update_customer_state_and_tree_milestones(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=3)
    client = TestClient(app)

    event_times = [
        "2026-05-25T09:10:00Z",
        "2026-05-25T09:20:00Z",
        "2026-05-25T10:05:00Z",
        "2026-05-25T10:30:00Z",
    ]

    for expected_visits, occurred_at in enumerate(event_times, start=1):
        response = client.post(
            "/api/visits",
            json={"customer_id": "customer-123", "occurred_at": occurred_at},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["customer_id"] == "customer-123"
        assert payload["visit_count"] == expected_visits
        assert payload["trees_planted"] == expected_visits // 3
        assert payload["last_connection_at"] == occurred_at.replace("Z", "+00:00")

    response = client.get("/api/customers/customer-123")

    assert response.status_code == 200
    assert response.json() == {
        "customer_id": "customer-123",
        "visit_count": 4,
        "trees_planted": 1,
        "last_connection_at": "2026-05-25T10:30:00+00:00",
    }


def test_hourly_aggregation_counts_all_visits_across_customers(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=2)
    client = TestClient(app)

    events = [
        ("alice", "2026-05-25T09:10:00Z"),
        ("bob", "2026-05-25T09:59:59Z"),
        ("alice", "2026-05-25T10:00:00Z"),
    ]

    for customer_id, occurred_at in events:
        response = client.post(
            "/api/visits",
            json={"customer_id": customer_id, "occurred_at": occurred_at},
        )
        assert response.status_code == 201

    response = client.get("/api/visits/hourly")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"hour": "2026-05-25T09:00:00+00:00", "visit_count": 2},
            {"hour": "2026-05-25T10:00:00+00:00", "visit_count": 1},
        ]
    }


def test_customer_summary_uses_customer_specific_tree_counts(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=5)
    client = TestClient(app)

    events = [
        *[("alice", f"2026-05-25T09:{minute:02d}:00Z") for minute in range(7)],
        *[("bob", f"2026-05-25T10:{minute:02d}:00Z") for minute in range(3)],
    ]

    for customer_id, occurred_at in events:
        response = client.post(
            "/api/visits",
            json={"customer_id": customer_id, "occurred_at": occurred_at},
        )
        assert response.status_code == 201

    response = client.get("/api/customers")

    assert response.status_code == 200
    assert response.json() == {
        "total_visits": 10,
        "total_trees_planted": 1,
        "items": [
            {
                "customer_id": "alice",
                "visit_count": 7,
                "trees_planted": 1,
                "last_connection_at": "2026-05-25T09:06:00+00:00",
            },
            {
                "customer_id": "bob",
                "visit_count": 3,
                "trees_planted": 0,
                "last_connection_at": "2026-05-25T10:02:00+00:00",
            },
        ],
    }


def test_visit_event_defaults_to_current_time_when_device_omits_timestamp(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=5)
    client = TestClient(app)

    before = datetime.now(timezone.utc)
    response = client.post("/api/visits", json={"customer_id": "customer-123"})
    after = datetime.now(timezone.utc)

    assert response.status_code == 201
    last_connection_at = datetime.fromisoformat(response.json()["last_connection_at"])
    assert before <= last_connection_at <= after


def test_customer_not_found_returns_404(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=5)
    client = TestClient(app)

    response = client.get("/api/customers/missing")

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"
