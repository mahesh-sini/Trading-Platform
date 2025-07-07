# AI Trading Platform - Docker Setup Guide

## Overview
This guide explains how to run the complete AI Trading Platform locally using Docker. All services have been configured to work together with proper networking and data persistence.

## Prerequisites

1. **Docker & Docker Compose**
   ```bash
   # Install Docker (Ubuntu/Debian)
   sudo apt update
   sudo apt install docker.io docker-compose
   
   # Start Docker service
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # Add user to docker group (optional, to run without sudo)
   sudo usermod -aG docker $USER
   # Log out and back in for group changes to take effect
   ```

2. **System Requirements**
   - RAM: 8GB minimum (16GB recommended)
   - Disk: 10GB free space
   - CPU: 4 cores minimum

## Services Architecture

The platform consists of the following services:

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js React application |
| Backend API | 8000 | FastAPI main application |
| Data Service | 8002 | Market data ingestion & WebSocket |
| ML Service | 8003 | Machine learning predictions |
| PostgreSQL | 5432 | Main database |
| Redis | 6379 | Caching and session storage |
| InfluxDB | 8086 | Time-series market data |

## Quick Start

1. **Clone and Navigate**
   ```bash
   cd "/home/elconsys/Trading Platform"
   ```

2. **Start All Services**
   ```bash
   # Make startup script executable
   chmod +x start-local.sh
   
   # Start the platform
   ./start-local.sh
   ```

3. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API Docs: http://localhost:8000/docs
   - Data Service API: http://localhost:8002/docs
   - ML Service API: http://localhost:8003/docs

## Manual Docker Commands

If you prefer manual control:

```bash
# Build all images
docker-compose build

# Start infrastructure (databases first)
docker-compose up -d postgres redis influxdb

# Wait for databases to initialize (30-60 seconds)
sleep 60

# Start application services
docker-compose up -d backend data-service ml-service frontend

# View logs
docker-compose logs -f [service-name]

# Stop all services
docker-compose down
```

## Environment Configuration

Key environment variables are set in `.env` file:

- **Database URLs**: Configured for Docker networking
- **API Keys**: Set to demo/development values
- **Service URLs**: Internal Docker networking
- **CORS**: Configured for local development

## Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   # Check Docker status
   docker ps
   
   # View service logs
   docker-compose logs [service-name]
   ```

2. **Port conflicts**
   ```bash
   # Check what's using ports
   sudo netstat -tulpn | grep :[port]
   
   # Stop conflicting services
   sudo systemctl stop [service-name]
   ```

3. **Database connection issues**
   ```bash
   # Restart databases
   docker-compose restart postgres redis influxdb
   
   # Check database logs
   docker-compose logs postgres
   ```

4. **Build failures**
   ```bash
   # Clean build (removes cache)
   docker-compose build --no-cache
   
   # Remove all containers and volumes
   docker-compose down -v
   docker system prune -a
   ```

### Service Health Checks

All services include health checks:

```bash
# Check backend health
curl http://localhost:8000/health

# Check data service health
curl http://localhost:8002/health

# Check ML service health
curl http://localhost:8003/health

# Check frontend health
curl http://localhost:3000/api/health
```

## Development Workflow

1. **Making Changes**
   - Frontend: Hot reload enabled
   - Backend: Restart container after changes
   - Database: Changes persist in volumes

2. **Viewing Logs**
   ```bash
   # All services
   docker-compose logs -f
   
   # Specific service
   docker-compose logs -f backend
   ```

3. **Rebuilding After Changes**
   ```bash
   # Rebuild specific service
   docker-compose build [service-name]
   
   # Restart specific service
   docker-compose restart [service-name]
   ```

## API Keys and Configuration

### Required API Keys (for full functionality)

1. **Alpha Vantage** (Free tier available)
   - Get key from: https://www.alphavantage.co/support/#api-key
   - Update `ALPHA_VANTAGE_API_KEY` in `.env`

2. **Alpaca Trading** (Paper trading free)
   - Get keys from: https://alpaca.markets/
   - Update `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in `.env`

### Demo Mode

The platform works in demo mode with mock data even without real API keys.

## Data Persistence

Docker volumes ensure data persistence:
- `postgres_data`: Database tables and data
- `redis_data`: Cache and session data
- `influxdb_data`: Time-series market data

## Performance Tuning

For production deployment:

1. **Increase worker counts** in docker-compose.yml
2. **Allocate more memory** to containers
3. **Use production database** settings
4. **Enable caching** and optimize queries

## Next Steps

After successful startup:

1. **Create admin user** via backend API
2. **Configure API keys** for real market data
3. **Test trading functionality** in paper mode
4. **Set up monitoring** (Prometheus/Grafana)

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify all services are healthy
3. Check environment variables in `.env`
4. Ensure all required ports are available