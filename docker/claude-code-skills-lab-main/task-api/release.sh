#!/bin/bash
set -e

VERSION=$1
DOCKER_USER="munibaweb123"
IMAGE="task-api"
REGISTRY="ghcr.io"
GIT_SHA=$(git rev-parse --short HEAD)

if [ -z "$VERSION" ]; then
  echo "Usage: ./release.sh 1.0.0"
  exit 1
fi

echo "Building ${IMAGE} v${VERSION} (${GIT_SHA})..."

# Build with all tags
docker build \
  -t ${REGISTRY}/${DOCKER_USER}/${IMAGE}:latest \
  -t ${REGISTRY}/${DOCKER_USER}/${IMAGE}:v${VERSION} \
  -t ${REGISTRY}/${DOCKER_USER}/${IMAGE}:v${VERSION%.*} \
  -t ${REGISTRY}/${DOCKER_USER}/${IMAGE}:${GIT_SHA} \
  .

# Push all tags
echo "Pushing to GitHub Container Registry..."
docker push ${REGISTRY}/${DOCKER_USER}/${IMAGE}:latest
docker push ${REGISTRY}/${DOCKER_USER}/${IMAGE}:v${VERSION}
docker push ${REGISTRY}/${DOCKER_USER}/${IMAGE}:v${VERSION%.*}
docker push ${REGISTRY}/${DOCKER_USER}/${IMAGE}:${GIT_SHA}

echo "✅ Released ${IMAGE} v${VERSION}"
echo "   - ${REGISTRY}/${DOCKER_USER}/${IMAGE}:latest"
echo "   - ${REGISTRY}/${DOCKER_USER}/${IMAGE}:v${VERSION}"
echo "   - ${REGISTRY}/${DOCKER_USER}/${IMAGE}:v${VERSION%.*}"
echo "   - ${REGISTRY}/${DOCKER_USER}/${IMAGE}:${GIT_SHA}"
