# Tree Nation Visit Tracker

A small full-stack implementation of the assessment in [Tech Interview Assessment Spec.pdf](Tech%20Interview%20Assessment%20Spec.pdf).

- `backend/`: FastAPI service with SQLite persistence and Docker support.
- `frontend/`: React + TypeScript + Vite dashboard for hourly visit aggregates.

## Run With Docker

From the repository root:

```bash
docker compose up --build
```

The frontend runs at http://localhost:5173, the API runs at http://localhost:8000, and the OpenAPI docs are available at http://localhost:8000/docs.

Configuration:

- `DATABASE_PATH`: SQLite file path. Docker Compose uses `/data/visits.db`.
- `VISITS_PER_TREE`: number of visits that equal one planted tree. Default is `5`.

## Run Backend Tests

```bash
docker compose --profile test run --rm test
```

## Frontend: Run Locally

Docker is the easiest path for reviewers, but local frontend development still works normally from the repository root:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Run the backend in another terminal with:

```bash
docker compose up --build api
```

Open http://localhost:5173. The frontend expects the API at `http://localhost:8000` by default.

## API Documentation

Once the backend is running, the interactive OpenAPI documentation is hosted at http://localhost:8000/docs.

## Assumptions

- `customer_id` is provided by the device and is enough to identify a customer.
- Visit timestamps are stored and returned in UTC.
- A tree milestone is calculated as `floor(customer visits / VISITS_PER_TREE)`.
- SQLite is sufficient for this scope and is persisted through a Docker volume.
- The frontend is a separate app that can run through Docker or the local Vite dev server.

## Architecture

```mermaid
flowchart LR
    Device["Physical device"] --> API["FastAPI API"]
    API --> Repo["VisitRepository"]
    Repo --> DB[("SQLite")]
    Frontend["React frontend"] --> API
    API --> Docs["OpenAPI at /docs"]
```

See [docs/decisions.md](docs/decisions.md) for the short decision document.
