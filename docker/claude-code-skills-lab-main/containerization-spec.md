# Containerization Specification: Task API

## Intent

Containerize the SQLModel + Neon Task API for production deployment.

**Business Goal**: Enable any developer to run this API without environment setup.

**Technical Goal**: Create a portable, optimized container image that works anywhere Docker runs.

## Constraints

### Image Size
- **Target**: Under 200MB final image
- **Rationale**: Smaller images push/pull faster, reduce storage costs

### Security
- **Non-root user**: Container runs as UID 10001 (K8s compliant)
- **No shell access**: User shell set to `/sbin/nologin`
- **Health check**: Built-in endpoint for orchestrator monitoring
- **No secrets in image**: Database URL passed at runtime
- **No curl**: Health checks use Python's urllib (smaller attack surface)

### Configuration
- **DATABASE_URL**: Environment variable (not hardcoded)
- **PORT**: Configurable, defaults to 8000

### Base Image
- **Choice**: `python:3.12-alpine` (small, secure)
- **Alternative**: `python:3.12-slim` (if Alpine compatibility issues)
- **Build stage**: `ghcr.io/astral-sh/uv:python3.12-alpine` (UV not in final image)

## Success Criteria

- [ ] Container builds successfully without errors
- [ ] Image size under 200MB (verify with `docker images`)
- [ ] All CRUD endpoints work when running containerized
- [ ] Health check endpoint responds at `/health`
- [ ] Container can connect to Neon database with provided DATABASE_URL
- [ ] Image can be pushed to registry (Docker Hub or GHCR)
- [ ] Image can be pulled and run on different machine
- [ ] Container runs as non-root user (UID 10001)
- [ ] UV not present in final image
- [ ] No shell access available in container

## Non-Goals (What We're NOT Doing)

- [ ] Docker Compose multi-service setup (separate lesson)
- [ ] Kubernetes deployment (Chapter 50)
- [ ] CI/CD automation (future topic)
- [ ] GPU support (not needed for this API)

## Dependencies

- SQLModel Task API code from Chapter 40 Lesson 7
- Neon PostgreSQL database with connection string
- Docker Desktop installed and running
- Registry account (Docker Hub or GitHub)

---

## Implementation

### Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

# ============================================
# BUILD STAGE - Has UV, can compile packages
# ============================================
FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

WORKDIR /app

# P2: Dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual env
# UV is 10-100x faster than pip
RUN uv sync --frozen --no-cache --no-dev

# P2: Source code last (changes most frequently)
COPY main.py ./

# ============================================
# RUNTIME STAGE - Minimal, no build tools
# ============================================
FROM python:3.12-alpine AS runtime

WORKDIR /app

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

# P3: Create non-root user in single layer
# UID 10001+ for Kubernetes pod security compliance
# /sbin/nologin prevents shell access if container is compromised
RUN addgroup -g 10001 appgroup && \
    adduser -D -u 10001 -G appgroup -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

# P1: Copy only runtime artifacts from builder (no UV, no build tools)
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/main.py /app/

# Switch to non-root user (use numeric UID for portability)
USER 10001

EXPOSE 8000

# Health check using wget (built into Alpine, no curl needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --spider -q http://localhost:8000/health || exit 1

# Production command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### .dockerignore

```
# Python artifacts
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
*.egg
.eggs/

# Virtual environments
.venv/
venv/
ENV/

# UV cache
.uv/

# IDE and editor
.vscode/
.idea/
*.swp
*.swo
*~

# Git
.git/
.gitignore

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Documentation
docs/
*.md
!README.md

# Environment and secrets
.env
.env.*
*.pem
*.key
credentials.*

# OS files
.DS_Store
Thumbs.db

# Build artifacts
dist/
build/
```

### Health Endpoint (add to main.py)

```python
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "healthy", "service": "task-api"}
```

---

## Build & Run Commands

### Build
```bash
# Build with BuildKit (recommended)
DOCKER_BUILDKIT=1 docker build -t task-api:latest .

# Build with metadata
docker build \
    --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
    -t task-api:1.0.0 .
```

### Run
```bash
# Run with DATABASE_URL from environment
docker run -d \
    --name task-api \
    -p 8000:8000 \
    -e DATABASE_URL=$DATABASE_URL \
    task-api:latest

# Run with explicit DATABASE_URL
docker run -d \
    --name task-api \
    -p 8000:8000 \
    -e DATABASE_URL="postgresql://user:pass@host/db" \
    task-api:latest
```

### Validate
```bash
# Test 1: Verify non-root user
docker run --rm task-api:latest whoami
# Expected: appuser

# Test 2: Verify UID is 10001
docker run --rm task-api:latest id
# Expected: uid=10001(appuser) gid=10001(appgroup)

# Test 3: Health check works
docker run -d --name test -p 8000:8000 -e DATABASE_URL=$DATABASE_URL task-api:latest
sleep 10
docker inspect test | jq '.[0].State.Health.Status'
# Expected: "healthy"
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"task-api"}
docker rm -f test

# Test 4: Check image size
docker images task-api:latest
# Expected: Under 200MB

# Test 5: UV not in final image
docker run --rm task-api:latest which uv
# Expected: Not found

# Test 6: No shell access
docker run --rm task-api:latest /bin/bash
# Expected: Error (no bash available)
```

### Push to Registry
```bash
# Docker Hub
docker tag task-api:latest yourusername/task-api:latest
docker push yourusername/task-api:latest

# GitHub Container Registry
docker tag task-api:latest ghcr.io/yourusername/task-api:latest
docker push ghcr.io/yourusername/task-api:latest
```

---

## Decision Rationale

| Decision | Rationale |
|----------|-----------|
| UID 10001 (not 1000) | K8s `runAsNonRoot` policies, avoids host UID collision |
| `/sbin/nologin` shell | Prevents interactive access if container compromised |
| `USER 10001` (numeric) | More portable than username, works without /etc/passwd |
| wget over curl | Alpine includes wget, curl adds ~5MB + CVE exposure |
| UV official image | Faster builds, UV stays out of final image |
| `uv sync --frozen` | Reproducible builds from lock file |
| Multi-stage build | Build tools not in production image |
| Alpine base | Smallest size (~50MB base vs ~150MB slim) |

---

## Troubleshooting

### Container won't start
```bash
docker logs task-api
```
Common issues:
- Missing DATABASE_URL environment variable
- Database connection refused (check Neon status)
- Port already in use

### Health check failing
```bash
# Test endpoint directly
docker exec task-api wget -qO- http://localhost:8000/health

# Check if app is running
docker exec task-api ps aux
```

### Permission denied errors
```bash
# Verify file ownership
docker run --rm task-api:latest ls -la /app
# All files should be owned by appuser:appgroup
```

### Image too large
```bash
# Analyze layers
docker history task-api:latest

# Use dive for detailed analysis
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock wagoodman/dive task-api:latest
```
