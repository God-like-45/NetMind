# NetMind Backend - Development Dockerfile
# Multi-stage build: builder installs deps, runtime is lean

# ─── Stage 1: Dependency installation ────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies needed to build Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip-tools for reproducible installs
RUN pip install --no-cache-dir hatchling pip --upgrade

# Copy only dependency specification first (layer caching)
COPY pyproject.toml ./

# Install base dependencies and ML/RAG/Agent/Graph extras
RUN pip install --no-cache-dir -e ".[ml,rag,agent,graph]"

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for running the application
# Security: Never run the application as root
RUN groupadd --gid 1001 netmind \
    && useradd --uid 1001 --gid netmind --shell /bin/bash --create-home netmind

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=netmind:netmind . .

USER netmind

# Expose API port
EXPOSE 8000

# Health check using the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: run uvicorn
CMD ["uvicorn", "netmind.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1"]
