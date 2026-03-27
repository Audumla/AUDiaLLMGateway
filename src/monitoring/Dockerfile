# Multi-stage build for Monitoring Data Provider API
# Provides component status, logs, and control endpoints for LLM gateway
# Optimized for fast builds with minimal image size

# ===== Builder Stage =====
FROM python:3.12-slim AS builder

WORKDIR /build

# Install only essential build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for better caching)
COPY src/monitoring/requirements.txt .

# Install Python dependencies with pip optimizations
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir -r requirements.txt

# ===== Runtime Stage =====
FROM python:3.12-slim

WORKDIR /app

# Install only runtime OS dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Copy installed packages from builder (more efficient than rebuilding)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source (last step for best caching)
COPY src/monitoring /app/src/monitoring
COPY config /app/config

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Expose port
EXPOSE 8080

# Default command: run monitoring API
CMD ["python", "-m", "uvicorn", "src.monitoring.main:app", \
     "--host", "0.0.0.0", "--port", "8080", \
     "--log-level", "info"]
