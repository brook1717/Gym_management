# ---------------------------------------------------------------------------
# Dockerfile — Gym Management Django API
# ---------------------------------------------------------------------------
# Multi-stage build for a slim production image.

FROM python:3.12-slim AS base

# Prevent .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies required by Argon2, Pillow, and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn psycopg2-binary celery[redis]

# Copy application code
COPY gym_management/ .

# Collect static files (uses dummy SECRET_KEY at build time)
RUN SECRET_KEY=build-placeholder python manage.py collectstatic --noinput 2>/dev/null || true

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# ---------------------------------------------------------------------------
# Default entrypoint: Gunicorn with 4 workers
# Override CMD in docker-compose for Celery worker
# ---------------------------------------------------------------------------
CMD ["gunicorn", "gym_management.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-"]
