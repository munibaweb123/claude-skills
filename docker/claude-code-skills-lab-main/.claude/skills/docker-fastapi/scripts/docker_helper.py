#!/usr/bin/env python3
"""
Docker FastAPI helper script

Generates Dockerfiles and docker-compose files for FastAPI applications
with various configurations: development, production, multi-stage builds.
"""

import argparse
import os
from pathlib import Path


def generate_dev_dockerfile():
    """Generate a development Dockerfile with hot-reloading"""
    return """# Development Dockerfile for FastAPI
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

# Development command with auto-reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
"""


def generate_prod_dockerfile():
    """Generate a production Dockerfile with multi-stage build"""
    return """# syntax=docker/dockerfile:1

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building packages
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
"""


def generate_docker_compose():
    """Generate a docker-compose file for development"""
    return """version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - ENV=development
      - DATABASE_URL=postgresql://user:password@db:5432/mydb
    depends_on:
      - db
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
"""


def generate_prod_docker_compose():
    """Generate a docker-compose file for production"""
    return """version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.prod
      target: production
    ports:
      - "80:8000"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:password@db:5432/mydb
    depends_on:
      - db
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    deploy:
      placement:
        constraints:
          - node.role == manager

volumes:
  postgres_data:
"""


def main():
    parser = argparse.ArgumentParser(description='Docker FastAPI Helper')
    parser.add_argument('type', choices=['dev-dockerfile', 'prod-dockerfile', 'dev-compose', 'prod-compose'],
                        help='Type of file to generate')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')

    args = parser.parse_args()

    if args.type == 'dev-dockerfile':
        content = generate_dev_dockerfile()
    elif args.type == 'prod-dockerfile':
        content = generate_prod_dockerfile()
    elif args.type == 'dev-compose':
        content = generate_docker_compose()
    elif args.type == 'prod-compose':
        content = generate_prod_docker_compose()

    if args.output:
        with open(args.output, 'w') as f:
            f.write(content)
        print(f"Generated {args.type} to {args.output}")
    else:
        print(content)


if __name__ == "__main__":
    main()
