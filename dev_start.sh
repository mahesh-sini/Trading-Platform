#!/bin/bash

# AI Trading Platform Development Startup Script
echo "🚀 Starting AI Trading Platform Development Environment..."

# Check if we're in the right directory
if [[ ! "$PWD" =~ "Trading Platform" ]]; then
    echo "❌ Please run this script from your 'Trading Platform' directory"
    exit 1
fi

# Function to check if a service is running
check_service() {
    if docker-compose ps | grep -q "$1.*Up"; then
        echo "✅ $1 is running"
        return 0
    else
        echo "❌ $1 is not running"
        return 1
    fi
}

# Start infrastructure services with Docker Compose
echo "📦 Starting infrastructure services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service status
echo "🔍 Checking service status..."
check_service "postgres"
check_service "redis"
check_service "influxdb"
check_service "kafka"

# Activate Python virtual environment
echo "🔄 Activating Python environment..."
if [ -f "trading_env/bin/activate" ]; then
    source trading_env/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Install/update Python dependencies
echo "📥 Installing Python dependencies..."
cd backend
pip install -r requirements.txt

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Create initial data (subscription plans, etc.)
echo "🌱 Creating initial data..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from models.subscription import SubscriptionPlan, PlanInterval
from models.base import Base
import os

async def create_initial_data():
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/trading_platform')
    ASYNC_DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
    
    engine = create_async_engine(ASYNC_DATABASE_URL)
    
    async with engine.begin() as conn:
        # Create subscription plans
        plans = [
            {
                'plan_id': 'basic',
                'name': 'Basic',
                'description': 'Basic trading features with AI predictions',
                'price': 29.0,
                'currency': 'USD',
                'interval': PlanInterval.MONTH,
                'max_watchlists': 5,
                'max_positions': 10,
                'automated_trading': False,
                'backtesting': False,
                'advanced_analytics': False,
                'api_access': False,
                'priority_support': False
            },
            {
                'plan_id': 'pro',
                'name': 'Pro',
                'description': 'Advanced trading with automation and analytics',
                'price': 99.0,
                'currency': 'USD',
                'interval': PlanInterval.MONTH,
                'max_watchlists': 25,
                'max_positions': 50,
                'automated_trading': True,
                'backtesting': True,
                'advanced_analytics': True,
                'api_access': False,
                'priority_support': True
            },
            {
                'plan_id': 'enterprise',
                'name': 'Enterprise',
                'description': 'Full access with API and white-label options',
                'price': 299.0,
                'currency': 'USD',
                'interval': PlanInterval.MONTH,
                'max_watchlists': 100,
                'max_positions': 200,
                'automated_trading': True,
                'backtesting': True,
                'advanced_analytics': True,
                'api_access': True,
                'priority_support': True
            }
        ]
        
        for plan_data in plans:
            await conn.execute('''
                INSERT INTO subscription_plans 
                (plan_id, name, description, price, currency, interval, max_watchlists, max_positions, 
                 automated_trading, backtesting, advanced_analytics, api_access, priority_support)
                VALUES (:plan_id, :name, :description, :price, :currency, :interval, :max_watchlists, 
                        :max_positions, :automated_trading, :backtesting, :advanced_analytics, 
                        :api_access, :priority_support)
                ON CONFLICT (plan_id) DO NOTHING
            ''', plan_data)
    
    await engine.dispose()
    print('✅ Initial data created')

asyncio.run(create_initial_data())
"

# Go back to root directory
cd ..

echo ""
echo "🎯 Development environment is ready!"
echo ""
echo "📍 Services Status:"
echo "   • PostgreSQL: http://localhost:5432"
echo "   • Redis: http://localhost:6379"
echo "   • InfluxDB: http://localhost:8086"
echo "   • Kafka: http://localhost:9092"
echo ""
echo "🚀 To start the backend API:"
echo "   cd backend && uvicorn main:app --reload --port 8000"
echo ""
echo "📊 To view API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo ""
echo "💡 Use 'deactivate' to exit the Python virtual environment"