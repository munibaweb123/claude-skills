# Docker Production Hardening - Quick Reference

Fast reference for the four critical production hardening patterns.

## 🔐 1. Non-Root User (UID 10001+)

### Alpine Linux
```dockerfile
RUN addgroup -g 10001 appgroup && \
    adduser -D -u 10001 -G appgroup -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app
USER 10001
```

### Debian/Ubuntu
```dockerfile
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser && \
    chown -R appuser:appgroup /app
USER 10001
```

**Why UID 10001+?**
- Kubernetes `runAsNonRoot` and `MustRunAsNonRoot` policies require high UIDs
- Avoids collision with host system users (typically UID 1-1000)
- Better security audit compliance (SOC2, PCI-DSS)
- `/sbin/nologin` prevents shell access if container is compromised
- Numeric `USER 10001` is more portable than `USER appuser`

---

## 🏥 2. Health Checks (Without Curl)

### Python (Recommended - No Extra Dependencies)
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

### Alpine (wget is built-in)
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --spider -q http://localhost:8000/health || exit 1
```

### AI/ML Service (longer startup)
```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
```

**Why no curl?**
- Curl adds ~5MB to image size
- Introduces OpenSSL/libcurl CVE exposure
- Python's urllib is already available
- Alpine has wget built-in

**Why**: Enables automatic recovery, load balancer integration, zero-downtime deployments

**Application code** (FastAPI):
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## ⚙️ 3. ENV/ARG Configuration

### Build-Time Arguments
```dockerfile
ARG PYTHON_VERSION=3.12
ARG APP_ENV=production
ARG BUILD_DATE=unknown

FROM python:${PYTHON_VERSION}-slim
```

**Build with override**:
```bash
docker build --build-arg PYTHON_VERSION=3.11 --build-arg BUILD_DATE=$(date -u +%Y-%m-%d) .
```

### Runtime Environment Variables
```dockerfile
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production \
    PORT=8000 \
    WORKERS=4
```

**Run with override**:
```bash
docker run -e WORKERS=8 -e PORT=3000 myapp:latest
```

### Convert ARG to ENV
```dockerfile
ARG APP_VERSION=latest
ENV APP_VERSION=${APP_VERSION}
```

### ❌ Never Do This (Secrets)
```dockerfile
ENV DATABASE_PASSWORD=secret123  # NEVER!
ENV API_KEY=sk_live_abc           # NEVER!
```

### ✅ Pass Secrets at Runtime
```bash
docker run -e DATABASE_PASSWORD=$DB_PASS -e API_KEY=$API_KEY myapp:latest
```

**Why**: Flexibility, reusability, security (no hardcoded secrets)

---

## 📦 4. File Ownership (--chown)

### Basic Copy with Ownership
```dockerfile
USER appuser
COPY --chown=appuser:appuser . /app
```

### Multi-Stage Build
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install -r requirements.txt

FROM python:3.12-slim
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Copy from builder with ownership
COPY --from=builder --chown=appuser:appuser /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appuser . /app
```

### With Numeric UID/GID
```dockerfile
RUN useradd -u 1000 -g 1000 appuser
USER 1000:1000
COPY --chown=1000:1000 . /app
```

### ❌ Inefficient (creates 2 layers)
```dockerfile
COPY . /app
RUN chown -R appuser:appuser /app  # Doubles the layer size!
```

### ✅ Efficient (single layer)
```dockerfile
COPY --chown=appuser:appuser . /app
```

**Why**: Prevents permission errors, optimizes build cache, reduces image size

---

## 📋 Complete Minimal Example

All four patterns in one Dockerfile:

```dockerfile
# syntax=docker/dockerfile:1

# ============================================
# BUILD STAGE - Has UV, can install packages
# ============================================
FROM ghcr.io/astral-sh/uv:python3.12-slim AS builder

WORKDIR /app

# P2: Dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Install deps into virtual env
RUN uv sync --frozen --no-cache --no-dev

# P2: Source code last (changes most frequently)
COPY src/ ./src/
COPY main.py ./

# ============================================
# RUNTIME STAGE - Minimal, no build tools
# ============================================
FROM python:3.12-slim

WORKDIR /app

# 3. ENV configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

# 1. Non-root user (UID 10001+ for K8s compliance)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin appuser && \
    mkdir -p /app && \
    chown -R appuser:appgroup /app

# 4. File ownership - copy from builder with --chown
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app/src /app/src
COPY --from=builder --chown=appuser:appgroup /app/main.py /app/

# Switch to non-root user (numeric for portability)
USER 10001

EXPOSE 8000

# 2. Health check (using Python - no curl needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧪 Quick Validation Tests

```bash
# Test 1: Non-root user
docker run --rm myapp:latest whoami
# Expected: appuser (not root)

# Test 2: Verify UID is 10001+
docker run --rm myapp:latest id
# Expected: uid=10001(appuser) gid=10001(appgroup)

# Test 3: Health check works
docker run -d --name test myapp:latest
sleep 15
docker inspect test | jq '.[0].State.Health.Status'
# Expected: "healthy"
docker rm -f test

# Test 4: File ownership
docker run --rm myapp:latest ls -la /app
# Expected: Files owned by appuser:appgroup (UID 10001)

# Test 5: ENV variables present
docker run --rm myapp:latest env | grep PORT
# Expected: PORT=8000

# Test 6: Can override ENV
docker run --rm -e PORT=3000 myapp:latest env | grep PORT
# Expected: PORT=3000

# Test 7: No shell access (should fail)
docker run --rm myapp:latest /bin/bash
# Expected: Error (no shell available)

# Test 8: UV not in final image
docker run --rm myapp:latest which uv
# Expected: Not found (UV only in build stage)
```

---

## 📊 Pattern Checklist

Before deploying to production, verify:

### Security
- [ ] Non-root user with UID 10001+ created
- [ ] `USER 10001` directive used (numeric, not name)
- [ ] Shell set to `/sbin/nologin` (no interactive access)
- [ ] No secrets in ENV statements
- [ ] All `COPY` commands use `--chown` flag

### Build Optimization
- [ ] Multi-stage build separates builder and runtime
- [ ] UV official image used (`ghcr.io/astral-sh/uv:*`)
- [ ] UV not present in final image
- [ ] Dependency files copied before source code (P2)
- [ ] Related RUN commands combined (P3)

### Health & Operations
- [ ] `HEALTHCHECK` uses Python/wget (not curl)
- [ ] Health endpoint implemented in app code
- [ ] Environment variables documented with defaults
- [ ] Build arguments for version/metadata

### Validation
- [ ] Image tested with validation commands above
- [ ] Image size is reasonable (<200MB for Alpine, <300MB for slim)

---

## 📚 Full Documentation

See [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md) for:
- Detailed explanations of each pattern
- Common mistakes and how to avoid them
- Advanced patterns and use cases
- Complete production template
- Security scanning and compliance
- Troubleshooting guide

---

## 🚀 Quick Start

```bash
# Copy production template
cp .claude/skills/docker-deployment/assets/Dockerfile.optimized-slim ./Dockerfile

# Build
docker build -t myapp:latest .

# Test
docker run -d --name myapp -p 8000:8000 myapp:latest

# Verify health
sleep 35
docker ps  # Check health status

# View logs
docker logs myapp

# Clean up
docker rm -f myapp
```

**All templates include the four hardening patterns by default!**
