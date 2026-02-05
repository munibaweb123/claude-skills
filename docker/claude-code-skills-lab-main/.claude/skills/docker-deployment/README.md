# Docker Deployment Skill for AI Services

This skill provides production-hardened Docker deployment templates and tools for AI services, with comprehensive security and operational best practices built in.

## 🔒 Production Hardening Features

All templates include these critical security and operational patterns:

- **Non-root user execution** - Runs as dedicated user (UID 1000) for security
- **Health checks** - Automatic container health monitoring and recovery
- **Environment variable configuration** - Flexible runtime configuration with sensible defaults
- **Proper file ownership** - `--chown` flags prevent permission issues
- **Multi-stage builds** - 50-80% smaller images with separated build/runtime
- **Layer caching optimization** - 10-100x faster rebuilds with UV package manager
- **Security scanning ready** - Minimal attack surface, no unnecessary packages

See [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md) for detailed security patterns and implementation guide.

## Core Docker Concepts

### Images vs Containers

Understanding the relationship between images and containers is fundamental to Docker:

| **Docker Image** | **Docker Container** |
|------------------|----------------------|
| Immutable, read-only template | Running instance of an image |
| Blueprint/class definition | Instantiated object |
| Built from a Dockerfile | Created with `docker run` |
| Stored in registries (Docker Hub, ECR) | Lives on the host machine |
| Can exist without containers | Cannot exist without an image |
| Shareable and versioned | Isolated and ephemeral |

**Analogy**: An image is like a recipe, while a container is the actual dish you cook from that recipe. You can make multiple dishes (containers) from the same recipe (image).

### Layer Architecture

Docker images are built using a **layered filesystem**:

```
┌─────────────────────────────────┐
│  Layer 4: COPY app.py /app      │  ← Your application code
├─────────────────────────────────┤
│  Layer 3: RUN pip install flask │  ← Dependencies
├─────────────────────────────────┤
│  Layer 2: RUN apt-get update    │  ← System packages
├─────────────────────────────────┤
│  Layer 1: FROM python:3.11      │  ← Base image
└─────────────────────────────────┘
```

**Key properties of layers**:
- Each Dockerfile instruction creates a new layer
- Layers are **read-only** and **immutable** once created
- Layers are **cached** and **shared** between images
- Only changed layers need to be rebuilt or transferred
- Layers are identified by content-addressable SHA256 hashes

**Optimization tip**: Order Dockerfile instructions from least-frequently changed (base image, system deps) to most-frequently changed (application code) to maximize cache hits.

### Copy-on-Write (CoW) Mechanism

When a container runs, Docker uses **copy-on-write** to manage the filesystem efficiently:

```
┌─────────────────────────────────┐
│  Container Layer (R/W)          │  ← Writable layer (thin)
│  - Modified files               │
│  - New files                    │
│  - Deleted file markers         │
├─────────────────────────────────┤
│  Image Layers (Read-Only)       │  ← Shared across containers
│  Layer 4: App code              │
│  Layer 3: Dependencies          │
│  Layer 2: System packages       │
│  Layer 1: Base image            │
└─────────────────────────────────┘
```

**How CoW works**:
1. **Read operations**: Data is read directly from image layers (fast, no duplication)
2. **Write operations**: The file is copied to the container's writable layer first, then modified
3. **Delete operations**: A "whiteout" marker is placed in the writable layer

**Benefits of CoW**:
- **Fast startup**: Containers start instantly (no copying the entire image)
- **Storage efficiency**: Multiple containers share the same image layers
- **Memory efficiency**: Identical files in memory are shared via page cache
- **Quick commits**: Only the thin writable layer needs to be saved

**Important**: Data in the container layer is lost when the container is removed. Use **volumes** for persistent data.

### The Complete Lifecycle

```
Dockerfile → docker build → Image → docker run → Container
                              ↓                      ↓
                         Registry ←── docker push    │
                              ↓                      ↓
                         docker pull            Writable Layer
                              ↓                      ↓
                         New Host              docker commit → New Image
```

## Features

### Production Hardening
- ✅ **Non-root user creation** - Security best practice with proper UID/GID
- ✅ **Health checks** - Automatic monitoring and recovery with `HEALTHCHECK`
- ✅ **ENV/ARG configuration** - Flexible build-time and runtime configuration
- ✅ **File ownership with --chown** - Proper permissions without extra layers
- ✅ **Security checklist** - Comprehensive validation for production readiness

### Docker Fundamentals
- **Core Docker concept explanations** (images vs containers, layers, copy-on-write)
- Docker Desktop prerequisite validation
- Resource allocation recommendations for AI services

### Image Optimization
- **Multi-stage Dockerfile templates** for 50-80% smaller images
- **UV package manager integration** for 10-100x faster builds
- **Alpine and Debian Slim variants** for minimal image sizes
- **Layer caching optimization** strategies
- **.dockerignore generation** for build context optimization

### Operations & Debugging
- AI-optimized Dockerfile and docker-compose templates
- System resource checks for AI workloads
- **Container debugging and troubleshooting** (logs, exec, inspect)
- **Restart policy configuration** for production resilience
- **Failed container diagnostics** workflow

## Usage

### Production Hardening Guide

See [PRODUCTION_HARDENING.md](./PRODUCTION_HARDENING.md) for comprehensive documentation on:
- Non-root user creation (Alpine vs Debian)
- Health check configuration and best practices
- ENV/ARG usage patterns and secrets management
- File ownership with `--chown` optimization
- Complete production template with all patterns
- Security validation checklist

### Setup and Configuration

```bash
# Validate Docker Desktop setup for AI services
python docker_deployment_helper.py validate

# Get resource recommendations for AI services
python docker_deployment_helper.py recommend

# Get configuration guidance for Docker Desktop
python docker_deployment_helper.py configure

# Generate AI-optimized docker-compose file
python docker_deployment_helper.py generate-compose
```

### Image Optimization

```bash
# Show comprehensive optimization guide
python docker_deployment_helper.py optimize-guide

# Generate .dockerignore for build context optimization
python docker_deployment_helper.py generate-dockerignore

# Copy optimized Dockerfile templates
python docker_deployment_helper.py copy-dockerfile --variant alpine      # Minimal size (~50-150MB)
python docker_deployment_helper.py copy-dockerfile --variant slim        # Better compatibility (~150-300MB)
python docker_deployment_helper.py copy-dockerfile --variant gunicorn    # Production with workers
python docker_deployment_helper.py copy-dockerfile --variant basic       # Single-stage (development)
```

### Docker Concepts

```bash
# Explain Docker concepts (interactive menu)
python docker_deployment_helper.py explain

# Explain specific topics
python docker_deployment_helper.py explain images-vs-containers
python docker_deployment_helper.py explain layer-architecture
python docker_deployment_helper.py explain copy-on-write
python docker_deployment_helper.py explain all
```

### Debugging and Troubleshooting

```bash
# Diagnose a failed container
python docker_deployment_helper.py diagnose <container-name-or-id>

# View container logs
python docker_deployment_helper.py logs <container-name-or-id>

# Inspect container configuration
python docker_deployment_helper.py inspect <container-name-or-id>

# Execute command in running container
python docker_deployment_helper.py exec <container-name-or-id> <command>

# Explain restart policies
python docker_deployment_helper.py explain restart-policies

# Show debugging guide
python docker_deployment_helper.py debug-guide
```

## AI Service Resource Requirements

- **Memory**: Minimum 8GB (16GB+ recommended for large models)
- **CPU**: Minimum 4 cores (8+ cores recommended for parallel processing)
- **Disk**: At least 20GB free space for models and containers
- **Swap**: Consider increasing if running memory-intensive AI models

## Docker Desktop Configuration for AI

For optimal AI service performance, configure Docker Desktop with:

- Memory: Set to at least 8GB (or 50% of system RAM, max 16GB)
- CPUs: Set to at least 4 cores (or half of your CPU cores)
- Swap: Set to at least 2GB for memory-intensive operations
- Disk image size: Ensure at least 20GB available
- Shared memory (shm_size): At least 8GB for AI operations

## Debugging Failed Container Startups

When a container fails to start, follow this diagnostic workflow:

### 1. Check Container Status
```bash
docker ps -a  # List all containers including stopped ones
```

### 2. View Container Logs
```bash
docker logs <container-name>           # View all logs
docker logs --tail 50 <container-name> # Last 50 lines
docker logs -f <container-name>        # Follow logs in real-time
docker logs --since 5m <container-name> # Logs from last 5 minutes
```

### 3. Inspect Container Configuration
```bash
docker inspect <container-name>        # Full JSON configuration
docker inspect --format='{{.State.Status}}' <container-name>  # Just status
docker inspect --format='{{.State.Error}}' <container-name>   # Error message
docker inspect --format='{{.NetworkSettings.IPAddress}}' <container-name>  # IP
```

### 4. Execute Commands in Container (if running)
```bash
docker exec -it <container-name> /bin/bash  # Interactive shell
docker exec -it <container-name> /bin/sh    # If bash not available
docker exec <container-name> ls -la /app    # Non-interactive command
docker exec <container-name> env            # Check environment variables
```

### 5. Common Issues and Solutions

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Port already in use | `docker logs` shows bind error | Change port mapping or stop conflicting service |
| Out of memory | `docker inspect` shows OOMKilled | Increase container memory limit |
| Missing environment variables | `docker exec <container> env` | Add to docker-compose.yml or Dockerfile |
| Volume mount issues | `docker inspect --format='{{.Mounts}}'` | Check permissions and paths |
| Network connectivity | `docker exec <container> ping google.com` | Check network configuration |
| Application crash | `docker logs --tail 100` | Check application logs for stack trace |

## Restart Policies

Configure restart policies to ensure containers automatically recover from failures:

### Available Restart Policies

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `no` | Never restart (default) | Development, debugging |
| `always` | Always restart, even after host reboot | Production services |
| `unless-stopped` | Restart unless manually stopped | Recommended for most services |
| `on-failure[:max-retries]` | Restart only on non-zero exit | Services that may fail temporarily |

### Configuration Examples

#### In docker-compose.yml
```yaml
services:
  ai-service:
    image: my-ai-service
    restart: unless-stopped  # Recommended for production
    # OR
    restart: on-failure:5    # Retry up to 5 times
```

#### In docker run command
```bash
docker run -d --restart unless-stopped my-ai-service
docker run -d --restart on-failure:3 my-ai-service
```

#### Update existing container
```bash
docker update --restart unless-stopped <container-name>
```

### Monitoring Restart Count
```bash
# Check how many times container has restarted
docker inspect --format='{{.RestartCount}}' <container-name>

# View container events including restarts
docker events --filter container=<container-name>
```

## Image Optimization Techniques

### Multi-Stage Builds

Multi-stage builds separate the build environment from the runtime environment, dramatically reducing final image size:

**Benefits:**
- **Smaller images**: Only runtime dependencies in final image (50-80% size reduction)
- **Faster deployments**: Less data to transfer and store
- **Better security**: No build tools or source files in production image
- **Cleaner images**: No build artifacts or cache files

**Available Templates:**

1. **Dockerfile.optimized-alpine** - Minimal size (~50-150MB)
   - Uses Alpine Linux base image
   - Best for applications without complex C dependencies
   - Fastest build and deployment times

2. **Dockerfile.optimized-slim** - Better compatibility (~150-300MB)
   - Uses Debian Slim base image
   - Better package compatibility
   - Recommended for AI/ML workloads with native dependencies

3. **Dockerfile.production-gunicorn** - Production-ready with multiple workers
   - Includes Gunicorn + Uvicorn workers
   - Environment variable configuration
   - Production logging and health checks

### UV Package Manager

UV is a Rust-based Python package installer that provides **10-100x faster** dependency installation:

```dockerfile
# Install UV
RUN pip install --no-cache-dir uv && pip cache purge

# Install dependencies with UV
RUN uv pip install --system --no-cache -r requirements.txt
```

**Benefits:**
- Dramatically faster builds (especially on CI/CD)
- Parallel dependency resolution
- Better caching strategies
- Drop-in replacement for pip

### Layer Caching Optimization

Proper instruction ordering maximizes Docker's layer caching:

```dockerfile
# 1. Base image (rarely changes)
FROM python:3.12-alpine

# 2. System dependencies (changes occasionally)
RUN apk add --no-cache gcc musl-dev

# 3. Python dependencies (changes when requirements.txt changes)
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# 4. Application code (changes frequently)
COPY . .
```

**Key Principle**: Order instructions from least-frequently changed to most-frequently changed.

### Build Context Optimization

Use `.dockerignore` to exclude unnecessary files from the build context:

```bash
# Generate .dockerignore template
python docker_deployment_helper.py generate-dockerignore
```

**Impact:**
- Faster build context transfer (especially for large repos)
- Smaller build context size
- Prevents accidental inclusion of secrets or data files
- Reduces cache invalidation from irrelevant file changes

### Image Size Comparison

| Base Image | Size | Use Case |
|------------|------|----------|
| `python:3.12` (full) | ~900MB | Development, debugging |
| `python:3.12-slim` | ~150MB | Production, good compatibility |
| `python:3.12-alpine` | ~50MB | Production, minimal dependencies |
| Multi-stage (slim) | ~200-400MB | Production AI/ML apps |
| Multi-stage (alpine) | ~80-200MB | Production lightweight apps |

### Cleanup Strategies

Remove unnecessary files in the builder stage:

```dockerfile
# Remove __pycache__ and .pyc files
RUN find /usr/local -type d -name '__pycache__' -exec rm -rf {} + && \
    find /usr/local -type f -name '*.pyc' -delete

# Remove test files and docs
RUN find /usr/local -name 'tests' -type d -exec rm -rf {} + && \
    find /usr/local -name '*.dist-info/RECORD' -delete
```

### Build Command Examples

```bash
# Build with Alpine (minimal size)
docker build -f assets/Dockerfile.optimized-alpine -t myapp:alpine .

# Build with Slim (better compatibility)
docker build -f assets/Dockerfile.optimized-slim -t myapp:slim .

# Build production image with Gunicorn
docker build -f assets/Dockerfile.production-gunicorn -t myapp:production .

# Build with BuildKit for better caching (recommended)
DOCKER_BUILDKIT=1 docker build -f assets/Dockerfile.optimized-alpine -t myapp .
```

### Image Size Analysis

```bash
# View image layers and sizes
docker history myapp:latest

# Compare image sizes
docker images | grep myapp

# Analyze image contents
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    wagoodman/dive myapp:latest
```

## Files

### Documentation
- `README.md`: This file - overview and usage guide
- `PRODUCTION_HARDENING.md`: **Comprehensive production security patterns** ⭐
  - Non-root user creation (Alpine and Debian variants)
  - Health check configuration and best practices
  - ENV/ARG usage, secrets management, and build-time configuration
  - File ownership optimization with `--chown`
  - Complete production template with all patterns
  - Security validation checklist and testing guide

### Scripts and Tools
- `docker_deployment_helper.py`: Main validation and configuration script

### Dockerfile Templates
- `assets/Dockerfile.optimized-alpine`: **Multi-stage Alpine** (~50-150MB) with full hardening ⭐
- `assets/Dockerfile.optimized-slim`: **Multi-stage Debian Slim** (~150-300MB) with full hardening ⭐
- `assets/Dockerfile.production-gunicorn`: **Production Gunicorn** with workers and full hardening ⭐
- `assets/Dockerfile.ai`: Basic single-stage template (development only)

### Configuration Files
- `assets/.dockerignore`: Build context optimization template
- `assets/requirements.txt`: Python dependencies for AI services
- `assets/docker-compose.ai.yml`: AI-optimized docker-compose configuration

All production templates (⭐) include:
- Non-root user execution (UID 1000)
- Health checks with `HEALTHCHECK`
- Proper ENV/ARG configuration
- `--chown` for efficient file ownership
- Multi-stage builds for minimal size
- Security best practices