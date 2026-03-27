# Multi-stage build for Monitoring Data Provider API
# Provides component status, logs, and control endpoints for LLM gateway

# ===== Builder Stage =====
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy source
COPY . /build

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r src/monitoring/requirements-monitoring.txt 2>&1 | grep -v "WARNING: Running pip"

# ===== Runtime Stage =====
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY . /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:$PATH"

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Expose port
EXPOSE 8080

# Default command: run monitoring API
CMD ["python", "-m", "uvicorn", "src.monitoring.main:app", \
     "--host", "0.0.0.0", "--port", "8080", \
     "--log-level", "info"]
