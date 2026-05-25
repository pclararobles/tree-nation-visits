# Decision Notes

## Persistence

SQLite is used because the service is small, the write model is simple, and a Docker volume is enough to preserve state across restarts. This avoids adding a second container and keeps the assessment focused on the API and domain behavior.

## API Shape

The API exposes three core operations:

- `POST /api/visits` receives device visit events.
- `GET /api/customers/{customer_id}` returns the customer counters.
- `GET /api/visits/hourly` returns the aggregate used by the frontend.

The device can omit `occurred_at`; the service then records the server receive time in UTC. The timestamp is accepted for tests, replay, and simple backfills.

## Tree Calculation

`trees_planted` is derived from `visit_count // VISITS_PER_TREE`. This makes the behavior idempotent with respect to counter updates inside a single transaction and avoids tracking a separate milestone table for this small scope.

## Frontend

The frontend is a separate React + TypeScript + Vite app. It uses Recharts for the hourly visits visualization and keeps API calls in a small client module. It is Dockerized for reviewer convenience with a production-style Nginx image, while the standard local Vite workflow remains available for development.
