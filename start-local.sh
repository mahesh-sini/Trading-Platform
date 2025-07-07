#!/bin/bash

# AI Trading Platform - Local Docker Startup Script
# This script builds and starts all services locally

set -e  # Exit on any error

echo "🚀 Starting AI Trading Platform locally with Docker..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

print_status "Stopping any existing containers..."
docker-compose down --remove-orphans

print_status "Cleaning up unused Docker resources..."
docker system prune -f

print_status "Building Docker images..."
docker-compose build --no-cache

print_status "Starting infrastructure services (databases, cache, etc.)..."
docker-compose up -d postgres redis influxdb

print_status "Waiting for databases to be ready..."
sleep 30

print_status "Starting application services..."
docker-compose up -d backend data-service ml-service

print_status "Waiting for backend services to be ready..."
sleep 45

print_status "Starting frontend..."
docker-compose up -d frontend

print_success "All services started successfully!"

echo ""
echo "🌐 Services are now available at:"
echo "  Frontend:     http://localhost:3000"
echo "  Backend API:  http://localhost:8000"
echo "  Data Service: http://localhost:8002"
echo "  ML Service:   http://localhost:8003"
echo ""
echo "  Databases:"
echo "  PostgreSQL:   localhost:5432"
echo "  Redis:        localhost:6379"
echo "  InfluxDB:     http://localhost:8086"
echo ""

print_status "Checking service health..."
sleep 10

# Check service health
services=("backend:8000" "data-service:8002" "ml-service:8003" "frontend:3000")
for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    if curl -f http://localhost:$port/health > /dev/null 2>&1; then
        print_success "$name is healthy"
    else
        print_warning "$name health check failed - service may still be starting"
    fi
done

echo ""
print_status "To view logs, run: docker-compose logs -f [service-name]"
print_status "To stop all services, run: docker-compose down"
print_success "Setup complete! 🎉"