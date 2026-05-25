from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from app.models import CustomerState, HourlyVisitCounts, VisitEvent
from app.repository import VisitRepository


DEFAULT_DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/visits.db"))
DEFAULT_VISITS_PER_TREE = int(os.getenv("VISITS_PER_TREE", "5"))


def create_app(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    visits_per_tree: int = DEFAULT_VISITS_PER_TREE,
) -> FastAPI:
    repository = VisitRepository(Path(database_path), visits_per_tree)
    app = FastAPI(
        title="Tree Nation Visit Tracker",
        version="0.1.0",
        description="Tracks shop visits and converts configurable visit milestones into planted tree counters.",
    )

    def get_repository() -> VisitRepository:
        return repository

    @app.post(
        "/api/visits",
        response_model=CustomerState,
        status_code=status.HTTP_201_CREATED,
        tags=["visits"],
    )
    def receive_visit(
        event: VisitEvent,
        repo: VisitRepository = Depends(get_repository),
    ) -> CustomerState:
        occurred_at = event.occurred_at or datetime.now(timezone.utc)
        return repo.record_visit(event.customer_id, occurred_at)

    @app.get(
        "/api/customers/{customer_id}",
        response_model=CustomerState,
        tags=["customers"],
    )
    def get_customer(
        customer_id: str,
        repo: VisitRepository = Depends(get_repository),
    ) -> CustomerState:
        customer = repo.get_customer(customer_id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        return customer

    @app.get(
        "/api/visits/hourly",
        response_model=HourlyVisitCounts,
        tags=["visits"],
    )
    def get_hourly_visits(
        start: datetime | None = Query(default=None),
        end: datetime | None = Query(default=None),
        repo: VisitRepository = Depends(get_repository),
    ) -> HourlyVisitCounts:
        return HourlyVisitCounts(items=repo.hourly_visit_counts(start, end))

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def frontend(_: Request) -> str:
        return _render_frontend(visits_per_tree)

    return app


app = create_app()


def _render_frontend(visits_per_tree: int) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tree Nation Visit Tracker</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f8f4;
      color: #17201b;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.88), rgba(246,248,244,0.96)),
        url("https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1800&q=80");
      background-size: cover;
      background-position: center;
    }}
    main {{
      width: min(960px, calc(100% - 32px));
      margin: 0 auto;
      padding: 40px 0;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: end;
      margin-bottom: 28px;
    }}
    h1 {{
      margin: 0;
      font-size: clamp(2rem, 4vw, 4.5rem);
      line-height: 0.95;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 12px 0 0;
      max-width: 560px;
      color: #405045;
      font-size: 1rem;
    }}
    .metric {{
      border: 1px solid #cdd8ce;
      background: rgba(255,255,255,0.78);
      padding: 16px;
      border-radius: 8px;
      min-width: 180px;
    }}
    .metric strong {{
      display: block;
      font-size: 2rem;
    }}
    section {{
      background: rgba(255,255,255,0.86);
      border: 1px solid #d8dfd8;
      border-radius: 8px;
      overflow: hidden;
    }}
    .toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      padding: 16px 18px;
      border-bottom: 1px solid #d8dfd8;
    }}
    button {{
      border: 1px solid #6c856f;
      background: #234b36;
      color: white;
      border-radius: 6px;
      padding: 10px 14px;
      cursor: pointer;
      font-weight: 650;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 14px 18px;
      border-bottom: 1px solid #e5e9e4;
      text-align: left;
    }}
    th {{
      color: #526156;
      font-size: 0.82rem;
      text-transform: uppercase;
    }}
    .bar {{
      height: 12px;
      border-radius: 999px;
      background: #dfe7de;
      overflow: hidden;
    }}
    .bar span {{
      display: block;
      height: 100%;
      background: #2f7a52;
      min-width: 4px;
    }}
    @media (max-width: 720px) {{
      header, .toolbar {{
        align-items: stretch;
        flex-direction: column;
      }}
      .metric {{
        min-width: 0;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Visit Tracker</h1>
        <p class="subtitle">Hourly shop visit totals from device events, with one planted tree every {visits_per_tree} visits per customer.</p>
      </div>
      <div class="metric">
        <span>Total hourly visits</span>
        <strong id="total">0</strong>
      </div>
    </header>
    <section>
      <div class="toolbar">
        <strong>Visits by hour</strong>
        <button type="button" id="refresh">Refresh</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Hour</th>
            <th>Visits</th>
            <th>Volume</th>
          </tr>
        </thead>
        <tbody id="rows">
          <tr><td colspan="3">Loading...</td></tr>
        </tbody>
      </table>
    </section>
  </main>
  <script>
    const rows = document.querySelector("#rows");
    const total = document.querySelector("#total");

    async function loadHourlyVisits() {{
      const response = await fetch("/api/visits/hourly");
      const data = await response.json();
      const items = data.items || [];
      const max = Math.max(1, ...items.map((item) => item.visit_count));
      const sum = items.reduce((value, item) => value + item.visit_count, 0);
      total.textContent = sum.toString();

      if (items.length === 0) {{
        rows.innerHTML = '<tr><td colspan="3">No visit events received yet.</td></tr>';
        return;
      }}

      rows.innerHTML = items.map((item) => {{
        const hour = new Date(item.hour).toLocaleString([], {{
          dateStyle: "medium",
          timeStyle: "short",
        }});
        const width = Math.max(4, Math.round((item.visit_count / max) * 100));
        return `<tr>
          <td>${{hour}}</td>
          <td>${{item.visit_count}}</td>
          <td><div class="bar" aria-label="${{item.visit_count}} visits"><span style="width: ${{width}}%"></span></div></td>
        </tr>`;
      }}).join("");
    }}

    document.querySelector("#refresh").addEventListener("click", loadHourlyVisits);
    loadHourlyVisits();
  </script>
</body>
</html>"""
