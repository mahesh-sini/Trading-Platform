"""
Memory profiling for Trading Platform backend
"""

import asyncio
import time
import random
from memory_profiler import profile
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.market_data import MarketDataService
from app.services.trading import TradingService
from app.services.portfolio import PortfolioService

# Database setup
engine = create_async_engine(settings.DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@profile
def memory_intensive_operations():
    """Test memory usage of various operations"""
    asyncio.run(run_memory_tests())

async def run_memory_tests():
    """Run memory-intensive tests"""
    
    # Test 1: Market data processing
    await test_market_data_processing()
    
    # Test 2: Portfolio calculations
    await test_portfolio_calculations()
    
    # Test 3: Trading operations
    await test_trading_operations()
    
    # Test 4: Database operations
    await test_database_operations()

async def test_market_data_processing():
    """Test memory usage of market data processing"""
    print("Testing market data processing...")
    
    market_service = MarketDataService()
    
    # Simulate processing large amounts of market data
    symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN'] * 100
    
    for symbol in symbols:
        # Simulate getting quote data
        quote_data = {
            'symbol': symbol,
            'price': random.uniform(100, 500),
            'volume': random.randint(1000000, 10000000),
            'timestamp': time.time()
        }
        
        # Process the data (this would normally involve calculations)
        processed_data = await market_service.process_quote_data(quote_data)
    
    print("Market data processing test completed")

async def test_portfolio_calculations():
    """Test memory usage of portfolio calculations"""
    print("Testing portfolio calculations...")
    
    portfolio_service = PortfolioService()
    
    # Create large portfolio data
    positions = []
    for i in range(1000):
        position = {
            'symbol': f'STOCK{i}',
            'quantity': random.randint(1, 1000),
            'average_price': random.uniform(10, 500),
            'current_price': random.uniform(10, 500)
        }
        positions.append(position)
    
    # Calculate portfolio metrics multiple times
    for _ in range(100):
        total_value = await portfolio_service.calculate_total_value(positions)
        pnl = await portfolio_service.calculate_unrealized_pnl(positions)
        risk_metrics = await portfolio_service.calculate_risk_metrics(positions)
    
    print("Portfolio calculations test completed")

async def test_trading_operations():
    """Test memory usage of trading operations"""
    print("Testing trading operations...")
    
    trading_service = TradingService()
    
    # Simulate many trading operations
    orders = []
    for i in range(1000):
        order = {
            'id': f'order_{i}',
            'symbol': random.choice(['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN']),
            'side': random.choice(['buy', 'sell']),
            'quantity': random.randint(1, 100),
            'price': random.uniform(100, 500),
            'order_type': random.choice(['market', 'limit'])
        }
        orders.append(order)
    
    # Process orders
    for order in orders:
        await trading_service.validate_order(order)
        await trading_service.calculate_order_value(order)
    
    print("Trading operations test completed")

async def test_database_operations():
    """Test memory usage of database operations"""
    print("Testing database operations...")
    
    async with async_session() as session:
        # Simulate loading large datasets
        for _ in range(100):
            # This would be actual database queries in a real scenario
            result = await session.execute(
                "SELECT * FROM users LIMIT 100"
            )
            users = result.fetchall()
            
            # Process the data
            user_data = []
            for user in users:
                user_dict = {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'created_at': user.created_at.isoformat()
                }
                user_data.append(user_dict)
    
    print("Database operations test completed")

# Mock service classes for testing
class MarketDataService:
    async def process_quote_data(self, quote_data):
        # Simulate data processing
        processed = {
            'symbol': quote_data['symbol'],
            'price': quote_data['price'],
            'volume': quote_data['volume'],
            'timestamp': quote_data['timestamp'],
            'calculations': {
                'vwap': quote_data['price'] * random.uniform(0.98, 1.02),
                'sma_20': quote_data['price'] * random.uniform(0.95, 1.05),
                'rsi': random.uniform(20, 80)
            }
        }
        return processed

class PortfolioService:
    async def calculate_total_value(self, positions):
        total = sum(pos['quantity'] * pos['current_price'] for pos in positions)
        return total
    
    async def calculate_unrealized_pnl(self, positions):
        pnl = sum(
            pos['quantity'] * (pos['current_price'] - pos['average_price']) 
            for pos in positions
        )
        return pnl
    
    async def calculate_risk_metrics(self, positions):
        # Simulate complex risk calculations
        total_value = await self.calculate_total_value(positions)
        
        metrics = {
            'var_95': total_value * 0.05 * random.uniform(0.8, 1.2),
            'sharpe_ratio': random.uniform(0.5, 2.0),
            'max_drawdown': random.uniform(0.05, 0.20),
            'beta': random.uniform(0.8, 1.2)
        }
        return metrics

class TradingService:
    async def validate_order(self, order):
        # Simulate order validation
        validations = {
            'symbol_valid': True,
            'quantity_valid': order['quantity'] > 0,
            'price_valid': order['price'] > 0,
            'balance_sufficient': True
        }
        return all(validations.values())
    
    async def calculate_order_value(self, order):
        if order['order_type'] == 'market':
            # Use current market price (simulated)
            market_price = random.uniform(order['price'] * 0.99, order['price'] * 1.01)
            return order['quantity'] * market_price
        else:
            return order['quantity'] * order['price']

if __name__ == "__main__":
    print("Starting memory profiling...")
    memory_intensive_operations()
    print("Memory profiling completed")