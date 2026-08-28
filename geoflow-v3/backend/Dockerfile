FROM python:3.12-slim-bookworm

ARG DEBIAN_MIRROR=http://mirrors.aliyun.com
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

RUN set -eux; \
  if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
    sed -i "s|http://deb.debian.org/debian-security|${DEBIAN_MIRROR}/debian-security|g" /etc/apt/sources.list.d/debian.sources; \
    sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}/debian|g" /etc/apt/sources.list.d/debian.sources; \
  fi; \
  apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -i "${PIP_INDEX_URL}" -e ".[dev]" 2>/dev/null || pip install --no-cache-dir -i "${PIP_INDEX_URL}" \
    fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg psycopg2-binary alembic \
    pydantic pydantic-settings "python-jose[cryptography]" "passlib[bcrypt]" bcrypt \
    "celery[redis]" redis httpx pyyaml structlog pgvector python-multipart \
    langgraph langchain-openai langchain-core cryptography pytest pytest-asyncio

COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
