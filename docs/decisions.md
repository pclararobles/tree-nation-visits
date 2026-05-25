# Decision Notes

## Persistence

SQLite is used because the service is small, the write model is simple, and a Docker volume is enough to preserve state across restarts. This avoids adding a second database container and keeps the assessment focused on the API and domain behavior.

The backend uses SQLModel for table models and Alembic for migrations. This keeps persistence explicit and closer to a production setup while still being lightweight for the assessment. Customers have an internal integer primary key, while the API-facing `customer_id` is stored as a unique external customer identifier.

## Backend Organization

FastAPI route handlers live in `view.py`, while business logic is organized in stateless service classes under `app/services`. The services use class methods and interact directly with the SQLModel table models, keeping the code clear without adding a repository layer that the current scope does not need.

## API Shape

The API exposes four core operations:

- `POST /api/visits` receives device visit events.
- `GET /api/customers` returns total visits, total trees planted, and per-customer counters.
- `GET /api/customers/{customer_id}` returns the customer counters.
- `GET /api/visits/hourly` returns the aggregate used by the frontend.

The device can omit `occurred_at`; the service then records the server receive time in UTC. The timestamp is accepted for tests, replay, and simple backfills.

## Tree Calculation

`trees_planted` is derived from `visit_count // VISITS_PER_TREE`. This makes the behavior idempotent with respect to counter updates inside a single transaction and avoids tracking a separate milestone table for this small scope.

Trees are calculated per customer, then summed for dashboard totals. For example, with `VISITS_PER_TREE=5`, one customer with 7 visits and another with 3 visits produces 1 tree, not 2.

## Base Dataset

The service seeds 10 baseline customers for reviewer convenience: `customer-001` through `customer-010`, with visit counts from `1` to `10`. The seed runs during app startup but is idempotent; existing baseline customers are skipped so restarts do not duplicate visits.

## Frontend

The frontend is a separate React + TypeScript + Vite app. It uses Recharts for the hourly visits visualization, shows total visits and planted trees, and lists per-customer visit counters. It is Dockerized for reviewer convenience with a production-style Nginx image, while the standard local Vite workflow remains available for development.
