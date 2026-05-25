FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

FROM base AS runtime

RUN pip install --no-cache-dir .

ENV DATABASE_PATH=/data/visits.db
ENV VISITS_PER_TREE=5

RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS test

COPY tests ./tests

RUN pip install --no-cache-dir ".[dev]"

CMD ["pytest"]
