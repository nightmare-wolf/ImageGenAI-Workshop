# Multi-stage build for the FastAPI backend (CPU-only; GPU work runs on RunPod).
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

FROM deps AS runtime
COPY . /app
# challenges/ is bind-mounted in dev (see docker-compose) and COPY'd in prod builds.
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
