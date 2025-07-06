#!/bin/bash

# Test Live Market Data Implementation
# Runs both backend and frontend tests for the new live market data features

set -e

echo "🧪 Testing Live Market Data Implementation"
echo "=========================================="
echo

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Backend Tests
print_status "Running Backend Tests for Live Market Data..."
echo

cd backend

if [ ! -f "requirements.txt" ]; then
    print_error "Backend requirements.txt not found!"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "trading_env" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv trading_env
fi

# Activate virtual environment
print_status "Activating Python virtual environment..."
source trading_env/bin/activate || {
    print_error "Failed to activate virtual environment"
    exit 1
}

# Install dependencies if needed
print_status "Installing/updating Python dependencies..."
pip install -r requirements.txt > /dev/null 2>&1 || {
    print_error "Failed to install Python dependencies"
    exit 1
}

# Run specific live market data tests
print_status "Running live market data service tests..."
echo
pytest tests/test_live_market_data.py -v --tb=short || {
    print_error "Backend live market data tests failed"
    exit 1
}

print_success "Backend tests completed successfully!"
echo

# Return to root directory
cd ..

# Frontend Tests
print_status "Running Frontend Tests for Market Data Service..."
echo

cd frontend

if [ ! -f "package.json" ]; then
    print_error "Frontend package.json not found!"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    print_status "Installing Node.js dependencies..."
    npm install > /dev/null 2>&1 || {
        print_error "Failed to install Node.js dependencies"
        exit 1
    }
fi

# Run specific market data service tests
print_status "Running market data service tests..."
echo
npm test -- --testPathPattern="services.*marketDataService|services.*api" --verbose || {
    print_error "Frontend market data service tests failed"
    exit 1
}

print_success "Frontend tests completed successfully!"
echo

# Return to root directory
cd ..

# Run integration tests (optional)
print_status "Running integration tests..."
echo

cd backend
pytest tests/test_live_market_data.py::TestLiveMarketDataAPI -v --tb=short || {
    print_error "Integration tests failed"
    exit 1
}

print_success "Integration tests completed successfully!"
cd ..

# Coverage Report
print_status "Generating test coverage reports..."
echo

# Backend coverage
cd backend
pytest tests/test_live_market_data.py --cov=services.live_market_data --cov-report=term-missing --cov-report=html:htmlcov_live_market || {
    print_error "Failed to generate backend coverage report"
}
cd ..

# Frontend coverage
cd frontend
npm test -- --testPathPattern="services.*marketDataService|services.*api" --coverage --coverageDirectory=coverage_live_market --watchAll=false || {
    print_error "Failed to generate frontend coverage report"
}
cd ..

print_success "Coverage reports generated!"
echo

# Summary
echo "🎉 Live Market Data Testing Complete!"
echo "====================================="
echo
print_success "✅ Backend live market data service tests passed"
print_success "✅ Frontend market data service tests passed"  
print_success "✅ API integration tests passed"
print_success "✅ Coverage reports generated"
echo
print_status "Coverage reports available at:"
echo "  📊 Backend: backend/htmlcov_live_market/index.html"
echo "  📊 Frontend: frontend/coverage_live_market/lcov-report/index.html"
echo
print_status "Test files:"
echo "  🧪 Backend: backend/tests/test_live_market_data.py"
echo "  🧪 Frontend: frontend/src/services/__tests__/marketDataService.test.ts"
echo "  🧪 Frontend: frontend/src/services/__tests__/api.test.ts"
echo
print_success "All live market data tests completed successfully! 🚀"