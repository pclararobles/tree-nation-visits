from __future__ import annotations

import os
from pathlib import Path


DEFAULT_DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/visits.db"))
DEFAULT_VISITS_PER_TREE = int(os.getenv("VISITS_PER_TREE", "5"))
DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
