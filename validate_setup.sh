#!/bin/bash

# Quick validation script to check if the platform is ready for testing

echo "🔍 AI Trading Platform - Setup Validation"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✅ $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

ERRORS=0

# Check Docker
if command -v docker &> /dev/null; then
    success "Docker is installed"
else
    error "Docker is not installed"
    ((ERRORS++))
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    success "Docker Compose is installed"
else
    error "Docker Compose is not installed"
    ((ERRORS++))
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    success "Python $PYTHON_VERSION is installed"
else
    error "Python 3 is not installed"
    ((ERRORS++))
fi

# Check virtual environment
if [ -d "trading_env" ]; then
    success "Virtual environment exists"
else
    warning "Virtual environment not found - run setup.sh"
    ((ERRORS++))
fi

# Check .env file
if [ -f ".env" ]; then
    success ".env file exists"
else
    error ".env file missing"
    ((ERRORS++))
fi

# Check key directories
for dir in backend frontend data_service ml_service; do
    if [ -d "$dir" ]; then
        success "$dir directory exists"
    else
        error "$dir directory missing"
        ((ERRORS++))
    fi
done

# Check key files
for file in docker-compose.yml CLAUDE.md requirements.txt; do
    if [ -f "backend/$file" ] || [ -f "$file" ]; then
        success "$file exists"
    else
        error "$file missing"
        ((ERRORS++))
    fi
done

# Check if Docker is running
if docker ps &> /dev/null; then
    success "Docker daemon is running"
else
    error "Docker daemon is not running"
    ((ERRORS++))
fi

echo ""
echo "📊 Validation Summary:"
if [ $ERRORS -eq 0 ]; then
    success "All checks passed! Ready for testing."
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Run the test suite: ./test_local.sh"
    echo "   2. Or start development: ./dev_start.sh"
    echo ""
else
    error "$ERRORS issues found. Please fix before testing."
    echo ""
    echo "💡 To fix issues:"
    echo "   1. Install missing dependencies"
    echo "   2. Run setup: ./setup.sh"
    echo "   3. Start Docker Desktop"
    echo ""
fi