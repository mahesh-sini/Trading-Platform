#!/bin/bash

# Build Docker images for AI Trading Platform
# Usage: ./scripts/build-images.sh [--no-cache]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
NO_CACHE=""
if [[ "$1" == "--no-cache" ]]; then
    NO_CACHE="--no-cache"
    echo -e "${YELLOW}Building with --no-cache flag${NC}"
fi

echo -e "${GREEN}Building AI Trading Platform Docker Images...${NC}"

# Function to build image with error handling
build_image() {
    local service=$1
    local context=$2
    local dockerfile=$3
    
    echo -e "${YELLOW}Building ${service}...${NC}"
    
    if docker build ${NO_CACHE} -t "trading-platform-${service}:latest" -f "${context}/${dockerfile}" "${context}"; then
        echo -e "${GREEN}✓ ${service} built successfully${NC}"
    else
        echo -e "${RED}✗ Failed to build ${service}${NC}"
        exit 1
    fi
}

# Build all services
echo -e "${YELLOW}Starting build process...${NC}"

# Backend
build_image "backend" "./backend" "Dockerfile"

# Data Service
build_image "data-service" "./data_service" "Dockerfile"

# ML Service
build_image "ml-service" "./ml_service" "Dockerfile"

# Frontend
build_image "frontend" "./frontend" "Dockerfile"

echo -e "${GREEN}All images built successfully!${NC}"

# Show built images
echo -e "${YELLOW}Built images:${NC}"
docker images | grep "trading-platform-"

echo -e "${GREEN}Build complete! You can now run:${NC}"
echo -e "${YELLOW}docker-compose up -d${NC}"