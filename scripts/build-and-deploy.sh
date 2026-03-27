#!/bin/bash
# Build and deploy monitoring API Docker image to Docker Hub
# Usage: ./scripts/build-and-deploy.sh <docker-hub-username> [tag]

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <docker-hub-username> [tag]"
    echo "Example: $0 example v0.14.0"
    exit 1
fi

DOCKER_USER="$1"
TAG="${2:-latest}"
IMAGE_NAME="audia-monitoring"
FULL_IMAGE="${DOCKER_USER}/${IMAGE_NAME}:${TAG}"

echo "Building Docker image: $FULL_IMAGE"
docker build -f src/monitoring/Dockerfile -t "$FULL_IMAGE" .

if [ "$TAG" != "latest" ]; then
    docker tag "$FULL_IMAGE" "${DOCKER_USER}/${IMAGE_NAME}:latest"
fi

echo ""
echo "Image built successfully!"
echo ""
echo "To push to Docker Hub, run:"
echo "  docker login -u $DOCKER_USER"
echo "  docker push $FULL_IMAGE"
if [ "$TAG" != "latest" ]; then
    echo "  docker push ${DOCKER_USER}/${IMAGE_NAME}:latest"
fi
