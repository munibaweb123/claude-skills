# syntax=docker/dockerfile:1

# =============================================================================
# BUILD STAGE - Install dependencies (discarded after build)
# =============================================================================
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-alpine AS builder

WORKDIR /app

# Install UV for fast dependency installation
RUN pip install --no-cache-dir uv

# P1: Dependencies first (changes rarely) - better layer caching
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# P2: Source code last (changes frequently)
COPY main.py models.py database.py config.py ./

# =============================================================================
# RUNTIME STAGE - Minimal production image
# =============================================================================
FROM python:${PYTHON_VERSION}-alpine

WORKDIR /app

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# P3: Create non-root user (UID 10001 for K8s compliance)
# /sbin/nologin prevents interactive shell access if container is compromised
RUN addgroup -g 10001 appgroup && \
    adduser -D -u 10001 -G appgroup -s /sbin/nologin appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code with correct ownership
COPY --from=builder --chown=appuser:appgroup /app/*.py /app/

# Switch to non-root user (numeric UID for portability)
USER 10001

EXPOSE 8000

# Health check for orchestrators
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
