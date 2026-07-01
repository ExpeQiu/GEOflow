FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir \
    fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg psycopg2-binary alembic \
    pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] bcrypt \
    celery[redis] redis httpx pyyaml structlog pgvector python-multipart \
    langgraph langchain-openai langchain-core cryptography pytest pytest-asyncio

COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
