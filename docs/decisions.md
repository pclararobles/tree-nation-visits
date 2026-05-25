# Decision Notes

## Persistence

SQLite is used because the service is small, the write model is simple, and a Docker volume is enough to preserve state across restarts. This avoids adding a second database container and keeps the stack focused on the API and domain behavior.

The backend uses SQLModel for table models and Alembic for migrations. This keeps persistence explicit and production-friendly while still being lightweight for a small service. Customers have an internal integer primary key, while the API-facing `customer_id` is stored as a unique external customer identifier.

`trees_planted` is **denormalized** on the customer row rather than computed from the visits table on every read. This avoids counting visits each time the dashboard loads. The trade-off is a write-time update, but that update already happens inside the same transaction that records the visit, so the cost is negligible.

## Backend Organization

FastAPI route handlers live in `views.py`, while business logic is organized in stateless service classes under `app/services`. The services use class methods and interact directly with the SQLModel table models.

## API Shape

The API exposes four core operations:

- `POST /api/visits` receives device visit events.
- `GET /api/customers` returns total visits, total trees planted, and per-customer counters.
- `GET /api/customers/{customer_id}` returns the customer counters.
- `GET /api/visits/hourly` returns hourly visit aggregates for operational analysis.

The device can omit `occurred_at`; the service then records the server receive time in UTC. The timestamp is accepted for tests, replay, and simple backfills.

There is no per-customer hourly endpoint. The current `GET /api/visits/hourly` aggregates across all customers, which is enough for the public impact page. A per-customer breakdown would add API surface without a concrete use case, so it was left out to avoid scope creep.

## Tree Calculation

`trees_planted` is derived from `visit_count // VISITS_PER_TREE`. This makes the behavior idempotent with respect to counter updates inside a single transaction and avoids tracking a separate milestone table for this small scope.

Trees are calculated per customer, then summed for dashboard totals. For example, with `VISITS_PER_TREE=5`, one customer with 7 visits and another with 3 visits produces 1 tree, not 2.

## Base Dataset

The service seeds 10 baseline customers for a useful first-run dashboard: `customer-001` through `customer-010`, each with a generated visit count between `1` and `100`. The seed runs during app startup but is idempotent; existing baseline customers are skipped so restarts do not duplicate visits.

## Frontend

The frontend is a separate React + TypeScript + Vite app. The public route shows aggregate impact metrics — total trees, total visits, active customers, and a hourly visit bar chart — while `/admin` contains operational sections for the debug visit form and the registered customers list. This split keeps the public page narrative (what, how, who, when) and operational data (per-customer counters, write actions) separate.

The hourly chart lives on the public page rather than admin because it is an aggregate, read-only metric. Per-customer data stays behind `/admin` where write actions also live.

The admin route is not protected by an authentication module in this codebase. In production, `/admin` would sit behind authentication or another access-control layer. For this service, the route separation documents the intended boundary without adding auth complexity.

The app is Dockerized with a production-style Nginx image.
