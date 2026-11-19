FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
COPY config/ /app/config/
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

ENV PATH="/app/backend/.venv/bin:$PATH" SOURCES_FILE=/app/config/sources.yaml
EXPOSE 8000
CMD ["sh", "-c", "risefirst migrate && uvicorn risefirst.entrypoints.api.main:app --host 0.0.0.0 --port 8000"]
