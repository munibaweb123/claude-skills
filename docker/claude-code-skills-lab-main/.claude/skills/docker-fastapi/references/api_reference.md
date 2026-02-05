# Docker FastAPI Deployment Reference Guide

## Dockerfile Best Practices for FastAPI Applications

### 1. Multi-stage Build Pattern

Multi-stage builds help reduce image size and improve security by separating build dependencies from runtime dependencies:

```dockerfile
# syntax=docker/dockerfile:1

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies needed for building packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### 2. Layer Caching Optimization

Order Dockerfile instructions to maximize layer caching:

```dockerfile
# Copy requirements first (changes less frequently)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last (changes more frequently)
COPY . .
```

### 3. Security Considerations

- Use minimal base images (e.g., `python:3.11-slim`)
- Run containers as non-root user
- Scan images for vulnerabilities
- Keep base images updated

## FastAPI Production Configuration

### 1. Process Management

For production deployments, use a process manager like Gunicorn with Uvicorn workers:

```bash
# Production command
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. Environment Variables

Use environment variables for configuration:

```python
import os
from fastapi import FastAPI

app = FastAPI()

# Use environment variables for configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
```

### 3. Health Checks

Implement health check endpoints:

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Docker Compose Patterns

### 1. Development Environment

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - ENV=development
      - DEBUG=1
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### 2. Production Environment

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "80:8000"
    environment:
      - ENV=production
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure

networks:
  default:
    driver: overlay
    attachable: true

volumes:
  postgres_data:
```

## Performance Optimization

### 1. Worker Configuration

For optimal performance, configure workers based on available CPU cores:

```bash
# Number of workers: (2 x CPU cores) + 1
gunicorn main:app --workers 5 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 2. Memory Management

Set appropriate memory limits and timeouts:

```bash
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100
```

## Common Deployment Scenarios

### 1. Single Container Deployment

For simple deployments, run the container directly:

```bash
# Build the image
docker build -t my-fastapi-app .

# Run with environment variables
docker run -d \
  --name fastapi-app \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@host:5432/dbname \
  -e API_KEY=your-api-key \
  my-fastapi-app
```

### 2. Docker Swarm Deployment

For container orchestration with Docker Swarm:

```bash
# Initialize swarm (if not already done)
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml myapp

# Check services
docker service ls
```

### 3. Kubernetes Deployment

For Kubernetes deployments, create appropriate manifests:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      containers:
      - name: fastapi-app
        image: my-fastapi-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
---
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
spec:
  selector:
    app: fastapi-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

## Troubleshooting Common Issues

### 1. Application Not Starting

- Verify the module name in the CMD instruction
- Check that all dependencies are installed
- Ensure the port matches what the application expects
- Check application logs: `docker logs <container-name>`

### 2. Permission Issues

- Ensure files are owned by the user running the container
- Use non-root user in production images
- Check file permissions in the Docker image

### 3. Large Image Size

- Use multi-stage builds
- Use minimal base images
- Remove unnecessary files and dependencies
- Clean up package manager cache

### 4. Performance Issues

- Configure appropriate number of workers
- Set memory and CPU limits
- Use proper load balancing
- Monitor resource usage
