# LeadLock AI — Backend Dockerfile
# Multi-stage build for FastAPI services

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default: run the core service (override via docker-compose command)
EXPOSE 8000 8001

CMD ["uvicorn", "core_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
