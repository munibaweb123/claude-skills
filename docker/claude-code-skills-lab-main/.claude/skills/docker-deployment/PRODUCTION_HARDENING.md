# Production Hardening Patterns for Docker

This document details essential security and operational patterns that must be included in production-ready Dockerfiles.

## Table of Contents

1. [Non-Root User Creation](#non-root-user-creation)
2. [Health Checks](#health-checks)
3. [Environment Variables and Build Arguments](#environment-variables-and-build-arguments)
4. [File Ownership with --chown](#file-ownership-with---chown)
5. [Complete Production Template](#complete-production-template)
6. [Security Checklist](#security-checklist)

---

## Non-Root User Creation

### Why Non-Root Users Matter

Running containers as root is a critical security vulnerability:
- **Container breakout**: If an attacker escapes the container, they have root access to the host
- **Privilege escalation**: Root processes can modify system files and configurations
- **Compliance**: Many security standards (PCI-DSS, SOC 2) require non-root execution
- **Defense in depth**: Limits damage from application vulnerabilities

### Why UID 10001+?

Using UID 10001 or higher (not 1000) is critical for Kubernetes deployments:
- **K8s Pod Security**: `runAsNonRoot` and `MustRunAsNonRoot` policies work better with high UIDs
- **Host collision avoidance**: UIDs 1-1000 often exist on the host system
- **Security audits**: High UIDs are recognized as container-specific users
- **Volume permissions**: Consistent UID across environments prevents permission issues

### Implementation Patterns

#### Alpine Linux (minimal)

```dockerfile
# Create non-root user with high UID and no shell access
RUN addgroup -g 10001 appgroup && \
    adduser -D -u 10001 -G appgroup -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

# Switch to non-root user (use numeric UID for portability)
USER 10001
```

**Flags explained**:
- `-D`: Don't assign a password (system account)
- `-u 10001`: Explicit UID above 10000 for K8s compliance
- `-G appgroup`: Assign to specific group
- `-s /sbin/nologin`: No shell access (security hardening)

#### Debian/Ubuntu (better compatibility)

```dockerfile
# Create non-root user with high UID and no shell access
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

# Switch to non-root user (use numeric UID for portability)
USER 10001
```

**Flags explained**:
- `-g 10001`: Explicit GID for the group
- `-u 10001`: Explicit UID above 10000 for K8s compliance
- `-s /sbin/nologin`: No shell access (prevents interactive access if compromised)

### Why Numeric USER Instead of Name?

```dockerfile
# ✅ Recommended: Numeric UID
USER 10001

# ❌ Avoid: Username (less portable)
USER appuser
```

**Benefits of numeric UID**:
- Works even if `/etc/passwd` is missing or corrupted
- More portable across different base images
- Explicit about what UID the container runs as
- Easier to verify in security audits

### Common Mistakes to Avoid

❌ **Bad**: Switching to non-root too early
```dockerfile
USER appuser
RUN apt-get update  # FAILS - no permission
```

✅ **Good**: Install system packages as root, then switch
```dockerfile
RUN apt-get update && apt-get install -y curl
USER appuser
COPY --chown=appuser:appuser . .
```

❌ **Bad**: Not setting ownership on volumes
```dockerfile
USER appuser
VOLUME /app/data  # appuser can't write here
```

✅ **Good**: Create directories before switching users
```dockerfile
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data
USER appuser
VOLUME /app/data
```

---

## Health Checks

### Why Health Checks Matter

Health checks enable:
- **Automatic recovery**: Orchestrators (Kubernetes, Docker Swarm) can restart unhealthy containers
- **Load balancing**: Remove unhealthy containers from load balancer rotation
- **Zero-downtime deployments**: Don't route traffic until containers are healthy
- **Monitoring**: Track application health over time

### Why Not Curl?

**Don't install curl just for health checks:**
- Adds ~5MB to image size
- Introduces OpenSSL/libcurl dependencies (CVE exposure)
- Expands attack surface unnecessarily
- Python's urllib is already available in Python images
- Alpine has wget built-in

### Implementation Patterns (Without Curl)

#### Python (Recommended - No Extra Dependencies)

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

**Parameters explained**:
- `--interval=30s`: Check every 30 seconds
- `--timeout=10s`: Mark as failed if check takes longer than 10 seconds
- `--start-period=5s`: Give app time to start before checking (adjust for your app)
- `--retries=3`: Fail after 3 consecutive failures
- Exit code 0 = healthy, 1 = unhealthy

#### Alpine (wget is built-in)

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --spider -q http://localhost:8000/health || exit 1
```

#### Health Check for Different Scenarios

**FastAPI/Flask (standard)**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

**Django**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1
```

**AI/ML Services** (longer startup due to model loading):
```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

**Database Container**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U postgres || exit 1
```

**Node.js**:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/health', r => process.exit(r.statusCode === 200 ? 0 : 1))" || exit 1
```

#### Advanced: Custom Health Check Script

For complex health checks that need to verify multiple dependencies:

```dockerfile
# Copy health check script
COPY --chown=appuser:appgroup healthcheck.py /app/healthcheck.py

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python /app/healthcheck.py
```

**healthcheck.py example**:
```python
#!/usr/bin/env python3
import sys
import urllib.request

try:
    response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
    if response.status == 200:
        sys.exit(0)  # Healthy
    sys.exit(1)  # Unhealthy
except Exception:
    sys.exit(1)  # Unhealthy
```

### Implementing Health Endpoints in Your App

**FastAPI**:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**Flask**:
```python
from flask import Flask

app = Flask(__name__)

@app.route("/health")
def health_check():
    return {"status": "healthy"}, 200
```

**Advanced health check** (with dependency checks):
```python
@app.get("/health")
async def health_check():
    # Check database connection
    try:
        await db.execute("SELECT 1")
    except Exception:
        return {"status": "unhealthy", "database": "down"}, 503

    # Check external API
    try:
        response = await httpx.get("https://api.example.com/status")
        if response.status_code != 200:
            return {"status": "unhealthy", "external_api": "down"}, 503
    except Exception:
        return {"status": "unhealthy", "external_api": "unreachable"}, 503

    return {"status": "healthy", "database": "up", "external_api": "up"}
```

### Testing Health Checks

```bash
# Check health status
docker ps  # Shows health status in STATUS column

# View health check logs
docker inspect --format='{{json .State.Health}}' container-name | jq

# Manually run health check
docker exec container-name curl -f http://localhost:8000/health
```

---

## Environment Variables and Build Arguments

### ENV vs ARG: Key Differences

| Feature | ARG | ENV |
|---------|-----|-----|
| **Scope** | Build-time only | Build-time + Runtime |
| **Visibility** | Only during `docker build` | Available in running container |
| **Override** | `--build-arg` at build time | `--env` or `-e` at runtime |
| **Use Case** | Build configuration | Runtime configuration |
| **Security** | Not in final image metadata | Visible in `docker inspect` |

### Implementation Patterns

#### Basic ENV Configuration

```dockerfile
# Runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    PORT=8000
```

#### ARG for Build-Time Configuration

```dockerfile
# Build arguments with defaults
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.1.0
ARG APP_ENV=production

# Use ARG in FROM statement
FROM python:${PYTHON_VERSION}-slim AS builder

# Install specific UV version
RUN pip install --no-cache-dir uv==${UV_VERSION}

# Convert ARG to ENV if needed at runtime
ENV APP_ENV=${APP_ENV}
```

**Build with custom arguments**:
```bash
docker build \
    --build-arg PYTHON_VERSION=3.11 \
    --build-arg UV_VERSION=0.2.0 \
    -t myapp:latest .
```

#### Configuration for Different Environments

```dockerfile
# Build-time: Which environment to build for
ARG APP_ENV=production

# Runtime: Application configuration
ENV APP_ENV=${APP_ENV} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Development vs Production settings
ENV LOG_LEVEL=${APP_ENV:+info}
ENV DEBUG=${APP_ENV:+false}
```

#### AI/ML Specific Configuration

```dockerfile
# Model and cache configuration
ENV TRANSFORMERS_CACHE=/app/models \
    HF_HOME=/app/models \
    TORCH_HOME=/app/models \
    HF_DATASETS_CACHE=/app/data/cache

# Performance tuning
ENV OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4

# GPU configuration (if applicable)
ENV CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_VISIBLE_DEVICES=all
```

#### Gunicorn/Uvicorn Configuration

```dockerfile
# Web server configuration (with sensible defaults)
ENV GUNICORN_WORKERS=4 \
    GUNICORN_WORKER_CLASS=uvicorn.workers.UvicornWorker \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_KEEP_ALIVE=5 \
    GUNICORN_MAX_REQUESTS=1000 \
    GUNICORN_MAX_REQUESTS_JITTER=100 \
    GUNICORN_BIND=0.0.0.0:8000
```

**Override at runtime**:
```bash
docker run -e GUNICORN_WORKERS=8 -e GUNICORN_TIMEOUT=300 myapp:latest
```

#### Security: Secrets Management

❌ **Bad**: Hardcoding secrets
```dockerfile
ENV DATABASE_URL=postgresql://user:password@host/db  # NEVER DO THIS
ENV API_KEY=sk_live_abc123  # NEVER DO THIS
```

✅ **Good**: Use runtime environment variables
```dockerfile
# Dockerfile - no secrets
ENV DATABASE_URL="" \
    API_KEY=""
```

```bash
# Pass secrets at runtime
docker run \
    -e DATABASE_URL=$DATABASE_URL \
    -e API_KEY=$API_KEY \
    myapp:latest

# Or use Docker secrets (Swarm)
docker service create \
    --secret database_url \
    --secret api_key \
    myapp:latest

# Or use Kubernetes secrets
kubectl create secret generic app-secrets \
    --from-literal=database-url=$DATABASE_URL \
    --from-literal=api-key=$API_KEY
```

#### Multi-Stage ARG Propagation

```dockerfile
# Global ARG (available in all stages)
ARG PYTHON_VERSION=3.12

# Builder stage
FROM python:${PYTHON_VERSION}-slim AS builder

# Stage-specific ARG
ARG UV_VERSION=0.1.0
RUN pip install uv==${UV_VERSION}

# Runtime stage
FROM python:${PYTHON_VERSION}-slim

# ARG not automatically available in new stage - must redeclare
ARG PYTHON_VERSION
ENV PYTHON_VERSION=${PYTHON_VERSION}
```

#### Default Values and Overrides

```dockerfile
# Provide sensible defaults
ARG BUILD_DATE=unknown
ARG VERSION=latest
ARG COMMIT_SHA=unknown

# Add metadata labels
LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${COMMIT_SHA}"
```

**Build with metadata**:
```bash
docker build \
    --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --build-arg VERSION=1.2.3 \
    --build-arg COMMIT_SHA=$(git rev-parse HEAD) \
    -t myapp:1.2.3 .
```

### Environment Variable Best Practices

1. **Use descriptive names**: `GUNICORN_WORKERS` not `WORKERS`
2. **Provide defaults**: Always set sensible defaults
3. **Document in README**: List all configurable variables
4. **Group related vars**: Keep related configuration together
5. **Never commit secrets**: Use runtime injection or secret managers
6. **Validate at startup**: Check required variables exist

**Startup validation example**:
```python
import os
import sys

# Validate required environment variables
required_vars = ["DATABASE_URL", "API_KEY", "SECRET_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)
```

---

## File Ownership with --chown

### Why --chown Matters

Without proper ownership:
- **Permission denied errors**: Application can't read/write files
- **Security issues**: Files owned by root even when running as non-root user
- **Volume mount problems**: Host files may have wrong permissions
- **Build inefficiency**: Separate RUN commands create extra layers

### Implementation Patterns

#### Basic --chown with COPY

```dockerfile
# Create non-root user first
RUN useradd --create-home --shell /bin/bash appuser

# Switch to non-root user
USER appuser

# Copy with ownership (avoids extra chown layer)
COPY --chown=appuser:appuser . /app
```

#### Multi-Stage Build with --chown

```dockerfile
# Builder stage (runs as root)
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.12-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Copy from builder with correct ownership
COPY --from=builder --chown=appuser:appuser /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder --chown=appuser:appuser /usr/local/bin /usr/local/bin

USER appuser
WORKDIR /app

# Copy application code with correct ownership
COPY --chown=appuser:appuser . .
```

#### Directory Creation with Ownership

```dockerfile
# Create directories with ownership in one command
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/data /app/logs /app/models /app/cache && \
    chown -R appuser:appuser /app

USER appuser
```

#### Numeric UID/GID (for volume consistency)

```dockerfile
# Using numeric IDs ensures consistency with host volumes
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g 1000 -m -s /bin/bash appuser && \
    mkdir -p /app && \
    chown -R 1000:1000 /app

USER 1000:1000

COPY --chown=1000:1000 . /app
```

**Benefits for volume mounts**:
```bash
# Host files created with UID 1000 will be accessible in container
docker run -v ./data:/app/data myapp:latest
```

#### Selective Ownership

```dockerfile
USER appuser

# Different ownership for different directories
COPY --chown=appuser:appuser ./src /app/src
COPY --chown=appuser:appuser ./config /app/config

# Read-only files can stay root-owned (if USER is still root at this point)
COPY ./static /app/static
RUN chmod -R 644 /app/static

# Then switch to appuser
USER appuser
```

### Common Patterns by Use Case

#### Pattern 1: Simple Application

```dockerfile
FROM python:3.12-slim

# Create user and directories
RUN useradd -m -s /bin/bash appuser && \
    mkdir -p /app && \
    chown appuser:appuser /app

USER appuser
WORKDIR /app

# Copy with ownership
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

CMD ["python", "app.py"]
```

#### Pattern 2: Multi-Stage with Build Artifacts

```dockerfile
# Build stage
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:18-slim

RUN useradd -m -s /bin/bash nodeuser && \
    mkdir -p /app && \
    chown nodeuser:nodeuser /app

USER nodeuser
WORKDIR /app

# Copy build artifacts with ownership
COPY --from=builder --chown=nodeuser:nodeuser /app/dist ./dist
COPY --from=builder --chown=nodeuser:nodeuser /app/node_modules ./node_modules
COPY --chown=nodeuser:nodeuser package.json .

CMD ["node", "dist/index.js"]
```

#### Pattern 3: Configuration Files with Restricted Permissions

```dockerfile
FROM python:3.12-slim

RUN useradd -m appuser && \
    mkdir -p /app /app/config && \
    chown -R appuser:appuser /app

# Copy config as root, set restrictive permissions
COPY config/secrets.conf /app/config/
RUN chown appuser:appuser /app/config/secrets.conf && \
    chmod 600 /app/config/secrets.conf

USER appuser

COPY --chown=appuser:appuser . /app
```

### Troubleshooting Ownership Issues

#### Check file ownership in container

```bash
# List files with ownership
docker exec container-name ls -la /app

# Check specific file ownership
docker exec container-name stat /app/myfile.txt

# Check running user
docker exec container-name whoami
docker exec container-name id
```

#### Fix ownership issues

```bash
# Inside running container (as root)
docker exec -u root container-name chown -R appuser:appuser /app/data

# Rebuild with correct --chown flags in Dockerfile
```

#### Volume mount permission issues

```dockerfile
# In Dockerfile - create directory with ownership
RUN mkdir -p /app/data && chown appuser:appuser /app/data
USER appuser
```

```bash
# At runtime - mount with correct ownership
docker run -v ./host-data:/app/data \
    --user $(id -u):$(id -g) \
    myapp:latest
```

### Performance Optimization

❌ **Inefficient**: Separate COPY and chown (creates 2 layers)
```dockerfile
COPY . /app
RUN chown -R appuser:appuser /app  # Doubles the layer size
```

✅ **Efficient**: COPY with --chown (creates 1 layer)
```dockerfile
COPY --chown=appuser:appuser . /app  # Single layer
```

---

## Complete Production Template

Here's a comprehensive production-ready Dockerfile incorporating all hardening patterns:

```dockerfile
# syntax=docker/dockerfile:1
# Production-hardened multi-stage Dockerfile with all security best practices

# ============================================================================
# Build arguments
# ============================================================================
ARG PYTHON_VERSION=3.12
ARG APP_VERSION=latest
ARG BUILD_DATE=unknown
ARG COMMIT_SHA=unknown

# ============================================================================
# Stage 1: Builder - Has UV, compilers, dev tools
# ============================================================================
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-slim AS builder

# Build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# P2: Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual env (not system Python)
# UV is 10-100x faster than pip
RUN uv sync --frozen --no-cache --no-dev

# P2: Copy source code last (changes most frequently)
COPY src/ ./src/
COPY main.py ./

# ============================================================================
# Stage 2: Runtime - Minimal, no build tools, no UV
# ============================================================================
FROM python:${PYTHON_VERSION}-slim AS runtime

# Metadata labels (OCI standard)
ARG APP_VERSION
ARG BUILD_DATE
ARG COMMIT_SHA
LABEL org.opencontainers.image.title="Production App" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${COMMIT_SHA}" \
      org.opencontainers.image.authors="your-team@example.com"

# Runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    WORKERS=4 \
    TIMEOUT=120 \
    KEEP_ALIVE=5 \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=100

WORKDIR /app

# P3: Create non-root user in single layer
# UID 10001+ for Kubernetes pod security compliance
# /sbin/nologin prevents shell access if container is compromised
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appgroup /app

# P1: Copy only runtime artifacts from builder (no UV, no build tools)
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src /app/src
COPY --from=builder --chown=appuser:appgroup /app/main.py /app/

# Switch to non-root user (use numeric UID for portability)
USER 10001

# Expose application port
EXPOSE 8000

# Health check using Python (no curl needed - smaller attack surface)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production command
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers ${WORKERS} --timeout-keep-alive ${KEEP_ALIVE} --access-log --log-level info"]
```

### Alpine Variant (Smallest Size)

```dockerfile
# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-alpine AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev
COPY src/ ./src/
COPY main.py ./

FROM python:${PYTHON_VERSION}-alpine AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Alpine uses addgroup/adduser with different syntax
RUN addgroup -g 10001 appgroup && \
    adduser -D -u 10001 -G appgroup -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src /app/src
COPY --from=builder --chown=appuser:appgroup /app/main.py /app/

USER 10001
EXPOSE 8000

# Alpine has wget built-in
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --spider -q http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run the Production Image

```bash
# Build with metadata
docker build \
    --build-arg APP_VERSION=1.0.0 \
    --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --build-arg COMMIT_SHA=$(git rev-parse --short HEAD) \
    --build-arg UV_VERSION=0.1.0 \
    -t myapp:1.0.0 \
    -t myapp:latest \
    .

# Run with environment overrides
docker run -d \
    --name myapp \
    -p 8000:8000 \
    -e WORKERS=8 \
    -e TIMEOUT=300 \
    -e DATABASE_URL=$DATABASE_URL \
    -e API_KEY=$API_KEY \
    -v $(pwd)/data:/app/data \
    --restart unless-stopped \
    myapp:1.0.0

# Check health status
docker ps  # Shows health: starting -> healthy/unhealthy

# View logs
docker logs -f myapp

# Inspect metadata
docker inspect myapp | jq '.[0].Config.Labels'
```

---

## Security Checklist

Use this checklist to verify your Dockerfile follows production hardening best practices:

### User and Permissions

- [ ] Non-root user created with `useradd` or `adduser`
- [ ] User has a home directory (`-m` or `--create-home`)
- [ ] Specific UID/GID set for volume compatibility (optional but recommended)
- [ ] `USER` directive used to switch to non-root user
- [ ] All application directories owned by non-root user
- [ ] `--chown` flag used with `COPY` commands
- [ ] No `sudo` or `su` in the final image

### Health Checks

- [ ] `HEALTHCHECK` instruction included
- [ ] Health check interval appropriate for application (typically 30s)
- [ ] Start period accounts for application initialization time
- [ ] Health endpoint implemented in application code
- [ ] Health check validates critical dependencies (database, external APIs)
- [ ] Health check uses appropriate method (curl, wget, or custom script)

### Environment Variables

- [ ] All environment variables documented in README
- [ ] Sensible defaults provided for all variables
- [ ] No secrets hardcoded in `ENV` statements
- [ ] `ARG` used for build-time configuration
- [ ] `ENV` used for runtime configuration
- [ ] Configuration can be overridden at runtime
- [ ] Application validates required variables at startup

### Build Optimization

- [ ] Multi-stage build used to minimize image size
- [ ] Base image is minimal (alpine or slim variant)
- [ ] Build dependencies separated from runtime dependencies
- [ ] Layer caching optimized (requirements before application code)
- [ ] `.dockerignore` file excludes unnecessary files
- [ ] No build cache or temporary files in final image
- [ ] `--no-cache-dir` used with package managers

### Security Best Practices

- [ ] Image uses specific version tags (not `latest`)
- [ ] Minimal packages installed (no unnecessary tools)
- [ ] Package lists cleaned up (`rm -rf /var/lib/apt/lists/*`)
- [ ] No shell (`/bin/sh`) in ultra-minimal images (optional)
- [ ] Secrets passed at runtime, not in image
- [ ] File permissions restricted where appropriate
- [ ] Image metadata includes version and build info

### Operational Readiness

- [ ] Application port exposed with `EXPOSE`
- [ ] Restart policy configured (via docker-compose or Kubernetes)
- [ ] Logging to stdout/stderr (not files)
- [ ] Graceful shutdown handling (SIGTERM)
- [ ] Persistent data uses volumes
- [ ] Image size < 500MB (aim for < 200MB)
- [ ] Build time < 5 minutes (with cold cache)

### Testing

```bash
# Test 1: Verify non-root user
docker run --rm myapp:latest whoami
# Expected: appuser (not root)

# Test 2: Verify health check
docker run -d --name test-health myapp:latest
sleep 40  # Wait for health check
docker inspect test-health | jq '.[0].State.Health.Status'
# Expected: "healthy"
docker rm -f test-health

# Test 3: Verify file ownership
docker run --rm myapp:latest ls -la /app
# Expected: Files owned by appuser

# Test 4: Verify environment variables
docker run --rm myapp:latest env | grep APP_
# Expected: All APP_* variables present

# Test 5: Verify image size
docker images myapp:latest
# Expected: Reasonable size (typically 100-500MB)

# Test 6: Test volume permissions
docker run --rm -v ./test-data:/app/data myapp:latest touch /app/data/test.txt
# Expected: No permission errors

# Test 7: Security scan
docker scan myapp:latest
# Or use trivy
trivy image myapp:latest
```

---

## Quick Reference

### Non-Root User (Alpine)
```dockerfile
RUN addgroup -g 10001 appgroup && \
    adduser -D -u 10001 -G appgroup -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app
USER 10001
```

### Non-Root User (Debian/Ubuntu)
```dockerfile
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app
USER 10001
```

### Health Check (Python - No Curl)
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

### Health Check (Alpine - wget built-in)
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --spider -q http://localhost:8000/health || exit 1
```

### Environment Variables
```dockerfile
ARG BUILD_ARG=value           # Build-time only
ENV RUNTIME_VAR=value         # Runtime available
ENV VAR=${BUILD_ARG}          # Convert ARG to ENV
```

### File Ownership
```dockerfile
COPY --chown=appuser:appgroup . /app
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
```

### Complete Minimal Example
```dockerfile
# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev
COPY src/ ./src/
COPY main.py ./

FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
WORKDIR /app
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser && \
    mkdir -p /app && chown -R appuser:appgroup /app
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src /app/src
COPY --from=builder --chown=appuser:appgroup /app/main.py /app/
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Additional Resources

- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Container Image Signing](https://docs.docker.com/engine/security/trust/)
