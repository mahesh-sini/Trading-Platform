# AI Trading Platform Makefile
# Simplifies common development and deployment tasks

.PHONY: help build up down logs clean test lint format init-dev init-prod deploy health

# Default target
help:
	@echo "AI Trading Platform - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  make init-dev     - Initialize development environment"
	@echo "  make build        - Build all Docker images"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - Show logs from all services"
	@echo "  make logs-f       - Follow logs from all services"
	@echo "  make clean        - Clean up containers and volumes"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-backend - Run backend tests"
	@echo "  make test-frontend- Run frontend tests"
	@echo "  make lint         - Run linting"
	@echo "  make format       - Format code"
	@echo ""
	@echo "Production:"
	@echo "  make init-prod    - Initialize production environment"
	@echo "  make deploy       - Deploy to production"
	@echo "  make health       - Check service health"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate   - Run database migrations"
	@echo "  make db-seed      - Seed database with test data"
	@echo "  make db-reset     - Reset database"
	@echo ""
	@echo "Monitoring:"
	@echo "  make monitoring   - Start monitoring services"
	@echo "  make dev-tools    - Start development tools"

# Development commands
init-dev:
	@echo "Initializing development environment..."
	cp .env.docker .env
	chmod +x scripts/*.sh
	@echo "Development environment initialized!"
	@echo "Edit .env file with your API keys"

build:
	@echo "Building Docker images..."
	./scripts/build-images.sh

build-no-cache:
	@echo "Building Docker images (no cache)..."
	./scripts/build-images.sh --no-cache

up:
	@echo "Starting services..."
	docker-compose up -d

up-build:
	@echo "Building and starting services..."
	docker-compose up -d --build

down:
	@echo "Stopping services..."
	docker-compose down

down-volumes:
	@echo "Stopping services and removing volumes..."
	docker-compose down -v

logs:
	docker-compose logs

logs-f:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-data:
	docker-compose logs -f data-service

logs-ml:
	docker-compose logs -f ml-service

logs-frontend:
	docker-compose logs -f frontend

clean:
	@echo "Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker volume prune -f

# Testing commands
test:
	@echo "Running all tests..."
	make test-backend
	make test-frontend

test-backend:
	@echo "Running backend tests..."
	docker-compose exec backend pytest

test-frontend:
	@echo "Running frontend tests..."
	docker-compose exec frontend npm test

test-coverage:
	@echo "Running tests with coverage..."
	docker-compose exec backend pytest --cov=. --cov-report=html
	docker-compose exec frontend npm run test:coverage

lint:
	@echo "Running linting..."
	docker-compose exec backend flake8 .
	docker-compose exec frontend npm run lint

format:
	@echo "Formatting code..."
	docker-compose exec backend black .
	docker-compose exec backend isort .
	docker-compose exec frontend npm run format

# Production commands
init-prod:
	@echo "Initializing production environment..."
	@echo "Please set up your production .env file with secure values"
	@echo "Required variables:"
	@echo "  - POSTGRES_PASSWORD"
	@echo "  - REDIS_PASSWORD"
	@echo "  - SECRET_KEY"
	@echo "  - ALPACA_API_KEY"
	@echo "  - ALPACA_SECRET_KEY"
	@echo "  - ALPHA_VANTAGE_API_KEY"

deploy:
	@echo "Deploying to production..."
	./scripts/deploy.sh production

deploy-staging:
	@echo "Deploying to staging..."
	./scripts/deploy.sh staging

health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health && echo " ✓ Backend healthy"
	@curl -s http://localhost:8002/health && echo " ✓ Data Service healthy"
	@curl -s http://localhost:8003/health && echo " ✓ ML Service healthy"
	@curl -s http://localhost:3000 && echo " ✓ Frontend healthy"

# Database commands
db-migrate:
	@echo "Running database migrations..."
	docker-compose exec backend alembic upgrade head

db-seed:
	@echo "Seeding database..."
	docker-compose exec backend python scripts/seed_data.py

db-reset:
	@echo "Resetting database..."
	docker-compose exec backend alembic downgrade base
	docker-compose exec backend alembic upgrade head

db-shell:
	@echo "Opening database shell..."
	docker-compose exec postgres psql -U postgres -d trading_platform

# Development tools
monitoring:
	@echo "Starting monitoring services..."
	docker-compose --profile monitoring up -d prometheus grafana

dev-tools:
	@echo "Starting development tools..."
	docker-compose --profile dev-tools up -d adminer redis-commander

# Service management
restart-backend:
	docker-compose restart backend

restart-data:
	docker-compose restart data-service

restart-ml:
	docker-compose restart ml-service

restart-frontend:
	docker-compose restart frontend

# Backup and restore
backup-db:
	@echo "Creating database backup..."
	docker-compose exec postgres pg_dump -U postgres trading_platform > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db:
	@echo "Restoring database backup..."
	@read -p "Enter backup file path: " backup_file; \
	docker-compose exec -T postgres psql -U postgres trading_platform < $$backup_file

# Shortcuts
start: up
stop: down
restart: down up
rebuild: down build up