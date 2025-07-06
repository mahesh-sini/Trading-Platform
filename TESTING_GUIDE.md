# 🧪 AI Trading Platform - Local Testing Guide

This guide will help you test the AI Trading Platform locally before deployment.

## 🚀 Quick Start

### 1. Prerequisites Check
```bash
# Ensure you have these installed:
- Docker & Docker Compose
- Python 3.9+
- Node.js 16+ (for frontend)
- Git
```

### 2. Environment Setup
```bash
# Make sure you're in the project directory
cd "Trading Platform"

# Run initial setup (if not done already)
./setup.sh

# Make test script executable
chmod +x test_local.sh
```

### 3. Run Complete Test Suite
```bash
# Run comprehensive testing
./test_local.sh
```

## 🔧 Manual Testing Steps

If you prefer to test components individually:

### Step 1: Start Infrastructure
```bash
# Start infrastructure services
./dev_start.sh

# Or manually with Docker Compose
docker-compose up -d postgres redis influxdb
```

### Step 2: Test Backend API
```bash
# Activate Python environment
source trading_env/bin/activate

# Go to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start backend server
uvicorn main:app --reload --port 8000
```

### Step 3: Test API Endpoints
```bash
# In a new terminal, test the API:

# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Register a test user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "full_name": "Test User"
  }'

# Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpassword123"
```

### Step 4: Test Frontend (Optional)
```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Open browser
open http://localhost:3000
```

## 🧪 Component-Specific Testing

### Broker Integration Testing
```bash
# Test broker health
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/brokers/health

# Test broker capabilities
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/brokers/interactive_brokers/capabilities
```

### ML Services Testing
```bash
# List available models
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/ml/models

# Get model types
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/ml/model-types

# Train a simple model (example)
curl -X POST "http://localhost:8000/api/v1/ml/models/train" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test_model_1",
    "model_config": {
      "model_id": "test_price_predictor",
      "model_type": "random_forest",
      "prediction_target": "price",
      "retrain_frequency": 30,
      "lookback_window": 252,
      "prediction_horizon": 5
    },
    "data_sources": ["market_data"],
    "training_period_days": 365,
    "symbols": ["AAPL"]
  }'
```

### Analytics Testing
```bash
# Get available metrics
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/analytics/metrics

# Get widget types
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/analytics/widget-types

# Create a custom dashboard (example)
curl -X POST "http://localhost:8000/api/v1/analytics/dashboards" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dashboard_id": "test_dashboard",
    "widgets": [
      {
        "widget_id": "portfolio_value",
        "widget_type": "metric",
        "title": "Portfolio Value",
        "metric_definitions": [
          {
            "name": "total_value",
            "description": "Total portfolio value",
            "metric_type": "portfolio",
            "calculation_formula": "sum(market_value)",
            "data_sources": ["positions"],
            "aggregation": "sum",
            "time_frame": "real_time"
          }
        ],
        "visualization_config": {
          "format": "currency",
          "precision": 2
        },
        "refresh_interval": 30,
        "position": {"x": 0, "y": 0, "width": 4, "height": 2}
      }
    ]
  }'
```

### Options Trading Testing
```bash
# Get options chain
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/v1/options-chain/AAPL"

# Test options pricing
curl -X POST "http://localhost:8000/api/v1/options/price" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "underlying_symbol": "AAPL",
    "option_type": "call",
    "strike_price": 150,
    "expiration_date": "2024-12-20T00:00:00",
    "underlying_price": 145,
    "volatility": 0.25
  }'
```

## 🔍 Testing Checklist

### ✅ Infrastructure Tests
- [ ] PostgreSQL connection
- [ ] Redis connection  
- [ ] InfluxDB connection
- [ ] Docker services running

### ✅ Backend API Tests
- [ ] Health endpoint responding
- [ ] API documentation accessible
- [ ] User registration working
- [ ] User authentication working
- [ ] JWT token generation

### ✅ Feature Tests
- [ ] Broker integration endpoints
- [ ] ML model endpoints
- [ ] Analytics endpoints
- [ ] Options trading endpoints
- [ ] Portfolio management
- [ ] Real-time data (WebSocket)

### ✅ Security Tests
- [ ] Authentication required for protected routes
- [ ] RBAC permissions working
- [ ] Multi-tenant isolation
- [ ] Input validation

### ✅ Performance Tests
- [ ] API response times < 500ms
- [ ] Database queries optimized
- [ ] Memory usage reasonable
- [ ] No memory leaks

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check if PostgreSQL is running
   docker ps | grep postgres
   
   # Check database logs
   docker logs trading_platform_postgres
   ```

2. **Port Already in Use**
   ```bash
   # Kill processes using port 8000
   lsof -ti:8000 | xargs kill -9
   ```

3. **Permission Denied**
   ```bash
   # Make scripts executable
   chmod +x test_local.sh dev_start.sh setup.sh
   ```

4. **Python Import Errors**
   ```bash
   # Ensure virtual environment is activated
   source trading_env/bin/activate
   
   # Reinstall dependencies
   pip install -r backend/requirements.txt
   ```

5. **Docker Issues**
   ```bash
   # Clean up Docker
   docker-compose down -v
   docker system prune -f
   
   # Restart Docker Desktop (if on Mac/Windows)
   ```

## 📊 Test Results Interpretation

### Expected Results
- All infrastructure services should be "Up"
- API health check should return `{"status": "healthy"}`
- Authentication should return access tokens
- All endpoint tests should return valid JSON responses
- No critical errors in logs

### Performance Benchmarks
- API response time: < 500ms (95th percentile)
- Database queries: < 100ms
- WebSocket latency: < 50ms
- Memory usage: < 2GB for all services

## 🚀 Next Steps After Testing

1. **If all tests pass:**
   - Proceed to production deployment
   - Set up monitoring and alerting
   - Configure real broker API keys
   - Set up backup and recovery

2. **If tests fail:**
   - Check logs: `docker-compose logs [service_name]`
   - Review error messages
   - Verify environment configuration
   - Check network connectivity

## 📞 Getting Help

If you encounter issues:
1. Check the logs: `docker-compose logs`
2. Review the `.env` file configuration
3. Ensure all prerequisites are installed
4. Try restarting services: `docker-compose restart`

---

**Happy Testing! 🎉**