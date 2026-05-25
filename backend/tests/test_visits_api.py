from datetime import datetime, timezone

from alembic.runtime.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlmodel import Session, select

from app.main import create_app
from app.models import CustomerRecord, VisitRecord


def test_app_initialization_runs_database_migrations(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=5)

    inspector = inspect(app.state.database_engine)
    customer_columns = {
        column["name"]: column for column in inspector.get_columns("customers")
    }
    visit_foreign_keys = inspector.get_foreign_keys("visits")

    with app.state.database_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    assert {"alembic_version", "customers", "visits"}.issubset(
        inspector.get_table_names()
    )
    assert current_revision == "0001_create_visit_tables"
    assert customer_columns["id"]["primary_key"] == 1
    assert customer_columns["external_customer_id"]["primary_key"] == 0
    assert visit_foreign_keys[0]["constrained_columns"] == ["customer_id"]
    assert visit_foreign_keys[0]["referred_table"] == "customers"
    assert visit_foreign_keys[0]["referred_columns"] == ["id"]


def test_app_reuses_singleton_database_engine(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=5)
    client = TestClient(app)
    engine = app.state.database_engine

    response = client.post("/api/visits", json={"customer_id": "customer-123"})

    assert response.status_code == 201
    assert app.state.database_engine is engine


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
    payload = response.json()
    assert payload["customer_id"] == "customer-123"
    assert payload["visit_count"] == 4
    assert payload["trees_planted"] == 1
    assert payload["last_connection_at"] == "2026-05-25T10:30:00+00:00"


def test_customer_external_identifier_is_separate_from_internal_primary_key(tmp_path):
    app = create_app(database_path=tmp_path / "visits.db", visits_per_tree=3)
    client = TestClient(app)

    response = client.post(
        "/api/visits",
        json={"customer_id": "customer-123", "occurred_at": "2026-05-25T09:10:00Z"},
    )

    assert response.status_code == 201
    with Session(app.state.database_engine) as session:
        customer = session.exec(
            select(CustomerRecord).where(
                CustomerRecord.external_customer_id == "customer-123"
            )
        ).one()
        visit = session.exec(select(VisitRecord)).one()

    assert isinstance(customer.id, int)
    assert customer.external_customer_id == "customer-123"
    assert visit.customer_id == customer.id


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
    items = response.json()["items"]
    assert len(items) == 2
    assert items[0]["hour"] == "2026-05-25T09:00:00+00:00"
    assert items[0]["visit_count"] == 2
    assert items[1]["hour"] == "2026-05-25T10:00:00+00:00"
    assert items[1]["visit_count"] == 1


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
    payload = response.json()
    assert payload["total_visits"] == 10
    assert payload["total_trees_planted"] == 1

    customers = payload["items"]
    assert len(customers) == 2

    alice = customers[0]
    assert alice["customer_id"] == "alice"
    assert alice["visit_count"] == 7
    assert alice["trees_planted"] == 1
    assert alice["last_connection_at"] == "2026-05-25T09:06:00+00:00"

    bob = customers[1]
    assert bob["customer_id"] == "bob"
    assert bob["visit_count"] == 3
    assert bob["trees_planted"] == 0
    assert bob["last_connection_at"] == "2026-05-25T10:02:00+00:00"


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
