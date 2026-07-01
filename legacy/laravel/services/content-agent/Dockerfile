FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic pyyaml

COPY config ./config
COPY app ./app

ENV PYTHONUNBUFFERED=1
ENV CONTENT_AGENT_DRIVER=langgraph
ENV CONTENT_AGENT_CALLBACK_SECRET=change-me
ENV LARAVEL_CALLBACK_URL=http://app:8080/internal/content-agent/callback

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
