# ===========================================
# AI 有声书工坊 - 后端 Dockerfile (多阶段构建)
# ===========================================

# ===========================================
# Stage 1: Builder
# ===========================================

FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===========================================
# Stage 2: Production
# ===========================================

FROM python:3.11-slim as production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONFAULTHANDLER=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appgroup backend/ .

# Create necessary directories and collect static files
RUN mkdir -p /app/logs /app/staticfiles && \
    chmod 777 /app/logs /app/staticfiles && \
    chown -R appuser:appgroup /app && \
    python manage.py collectstatic --noinput; \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=config.settings

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Default: run Django server
CMD ["python", "-m", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2"]

# ===========================================
# Stage 3: Celery Worker
# ===========================================

FROM python:3.11-slim as celery

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appgroup backend/ .

# Create necessary directories
RUN mkdir -p /app/logs && chmod 777 /app/logs && chown -R appuser:appgroup /app && \
    touch /app/logs/app.log && chown appuser:appgroup /app/logs/app.log

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=config.settings
ENV DB_ENGINE=django.db.backends.postgresql
ENV DB_HOST=postgres
ENV REDIS_HOST=redis

# Start Celery worker
CMD ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "--concurrency=4"]

# ===========================================
# Stage 4: Celery Beat (Scheduler)
# ===========================================

FROM python:3.11-slim as celery-beat

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appgroup backend/ .

# Create necessary directories and set permissions
RUN mkdir -p /app/logs && chmod 777 /app/logs && chown -R appuser:appgroup /app && \
    touch /app/logs/app.log && chown appuser:appgroup /app/logs/app.log

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=config.settings
ENV DB_ENGINE=django.db.backends.postgresql
ENV DB_HOST=postgres
ENV REDIS_HOST=redis

# Start Celery beat scheduler
CMD ["celery", "-A", "tasks.celery_app", "beat", "--loglevel=info"]
