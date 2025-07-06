"""
Database Performance Tests for Trading Platform
"""

import asyncio
import time
import json
import statistics
from typing import List, Dict, Any
from datetime import datetime, timedelta
import asyncpg
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import numpy as np

# Test configuration
DB_URL = "postgresql://testuser:testpass@localhost:5432/trading_test"
REDIS_URL = "redis://localhost:6379"

class DatabasePerformanceTester:
    def __init__(self):
        self.engine = create_async_engine(DB_URL)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.redis = None
        self.results = {}
    
    async def setup(self):
        """Setup test environment"""
        self.redis = redis.from_url(REDIS_URL)
        await self.setup_test_data()
    
    async def setup_test_data(self):
        """Create test data for performance testing"""
        async with self.async_session() as session:
            # Create test users
            await session.execute(text("""
                INSERT INTO users (id, email, username, is_active, created_at)
                SELECT 
                    generate_random_uuid(),
                    'test_user_' || i || '@example.com',
                    'test_user_' || i,
                    true,
                    NOW() - (random() * interval '365 days')
                FROM generate_series(1, 1000) i
                ON CONFLICT DO NOTHING
            """))
            
            # Create test portfolios
            await session.execute(text("""
                INSERT INTO portfolios (id, user_id, total_value, cash, equity, created_at)
                SELECT 
                    generate_random_uuid(),
                    u.id,
                    random() * 100000 + 10000,
                    random() * 10000 + 1000,
                    random() * 90000 + 9000,
                    u.created_at
                FROM users u
                WHERE u.email LIKE 'test_user_%'
                ON CONFLICT DO NOTHING
            """))
            
            # Create test positions
            await session.execute(text("""
                INSERT INTO positions (id, portfolio_id, symbol, quantity, average_price, current_price, created_at)
                SELECT 
                    generate_random_uuid(),
                    p.id,
                    (ARRAY['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'NFLX'])[floor(random() * 8 + 1)],
                    floor(random() * 1000 + 1),
                    random() * 500 + 50,
                    random() * 500 + 50,
                    p.created_at + (random() * interval '30 days')
                FROM portfolios p
                CROSS JOIN generate_series(1, 5) s
                ON CONFLICT DO NOTHING
            """))
            
            # Create test trades
            await session.execute(text("""
                INSERT INTO trades (id, portfolio_id, symbol, side, quantity, price, executed_at, created_at)
                SELECT 
                    generate_random_uuid(),
                    p.id,
                    (ARRAY['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'NFLX'])[floor(random() * 8 + 1)],
                    (ARRAY['buy', 'sell'])[floor(random() * 2 + 1)],
                    floor(random() * 100 + 1),
                    random() * 500 + 50,
                    NOW() - (random() * interval '365 days'),
                    NOW() - (random() * interval '365 days')
                FROM portfolios p
                CROSS JOIN generate_series(1, 20) s
                ON CONFLICT DO NOTHING
            """))
            
            await session.commit()
    
    async def test_query_performance(self, query: str, params: Dict = None, iterations: int = 100) -> Dict[str, Any]:
        """Test query performance"""
        execution_times = []
        
        async with self.async_session() as session:
            for _ in range(iterations):
                start_time = time.time()
                
                if params:
                    await session.execute(text(query), params)
                else:
                    await session.execute(text(query))
                
                execution_times.append((time.time() - start_time) * 1000)  # Convert to ms
        
        return {
            'query': query[:100] + '...' if len(query) > 100 else query,
            'iterations': iterations,
            'avg_time_ms': statistics.mean(execution_times),
            'min_time_ms': min(execution_times),
            'max_time_ms': max(execution_times),
            'p95_time_ms': np.percentile(execution_times, 95),
            'p99_time_ms': np.percentile(execution_times, 99),
            'std_dev_ms': statistics.stdev(execution_times),
        }
    
    async def test_redis_performance(self, iterations: int = 1000) -> Dict[str, Any]:
        """Test Redis performance"""
        
        # Test SET operations
        set_times = []
        for i in range(iterations):
            start_time = time.time()
            await self.redis.set(f"test_key_{i}", f"test_value_{i}")
            set_times.append((time.time() - start_time) * 1000)
        
        # Test GET operations
        get_times = []
        for i in range(iterations):
            start_time = time.time()
            await self.redis.get(f"test_key_{i}")
            get_times.append((time.time() - start_time) * 1000)
        
        # Test pipeline operations
        pipeline_times = []
        for batch in range(10):
            start_time = time.time()
            pipe = self.redis.pipeline()
            for i in range(100):
                pipe.set(f"pipeline_key_{batch}_{i}", f"pipeline_value_{batch}_{i}")
            await pipe.execute()
            pipeline_times.append((time.time() - start_time) * 1000)
        
        # Cleanup
        await self.redis.flushdb()
        
        return {
            'set_operations': {
                'iterations': iterations,
                'avg_time_ms': statistics.mean(set_times),
                'p95_time_ms': np.percentile(set_times, 95),
            },
            'get_operations': {
                'iterations': iterations,
                'avg_time_ms': statistics.mean(get_times),
                'p95_time_ms': np.percentile(get_times, 95),
            },
            'pipeline_operations': {
                'batches': 10,
                'avg_time_ms': statistics.mean(pipeline_times),
                'p95_time_ms': np.percentile(pipeline_times, 95),
            }
        }
    
    async def run_database_tests(self):
        """Run all database performance tests"""
        test_queries = [
            {
                'name': 'simple_user_lookup',
                'query': "SELECT * FROM users WHERE email = :email",
                'params': {'email': 'test_user_100@example.com'}
            },
            {
                'name': 'portfolio_with_positions',
                'query': """
                    SELECT p.*, pos.symbol, pos.quantity, pos.current_price
                    FROM portfolios p
                    LEFT JOIN positions pos ON p.id = pos.portfolio_id
                    WHERE p.user_id = (SELECT id FROM users WHERE email = :email)
                """,
                'params': {'email': 'test_user_100@example.com'}
            },
            {
                'name': 'recent_trades',
                'query': """
                    SELECT t.*, p.user_id
                    FROM trades t
                    JOIN portfolios p ON t.portfolio_id = p.id
                    WHERE t.executed_at >= :start_date
                    ORDER BY t.executed_at DESC
                    LIMIT 100
                """,
                'params': {'start_date': datetime.now() - timedelta(days=30)}
            },
            {
                'name': 'portfolio_performance',
                'query': """
                    SELECT 
                        p.user_id,
                        p.total_value,
                        COUNT(pos.id) as position_count,
                        SUM(pos.quantity * pos.current_price) as total_position_value
                    FROM portfolios p
                    LEFT JOIN positions pos ON p.id = pos.portfolio_id
                    GROUP BY p.id, p.user_id, p.total_value
                    HAVING COUNT(pos.id) > 0
                """,
                'params': None
            },
            {
                'name': 'symbol_aggregation',
                'query': """
                    SELECT 
                        symbol,
                        COUNT(*) as trade_count,
                        SUM(quantity) as total_volume,
                        AVG(price) as avg_price
                    FROM trades
                    WHERE executed_at >= :start_date
                    GROUP BY symbol
                    ORDER BY trade_count DESC
                """,
                'params': {'start_date': datetime.now() - timedelta(days=7)}
            }
        ]
        
        results = {}
        
        for test in test_queries:
            print(f"Running test: {test['name']}")
            result = await self.test_query_performance(
                test['query'], 
                test['params'], 
                iterations=50
            )
            results[test['name']] = result
        
        return results
    
    async def run_all_tests(self):
        """Run all performance tests"""
        print("Setting up test environment...")
        await self.setup()
        
        print("Running database performance tests...")
        db_results = await self.run_database_tests()
        
        print("Running Redis performance tests...")
        redis_results = await self.test_redis_performance()
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'database_tests': db_results,
            'redis_tests': redis_results
        }
        
        # Save results
        filename = f"db-performance-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"Results saved to {filename}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print performance test summary"""
        print("\n" + "="*60)
        print("DATABASE PERFORMANCE TEST SUMMARY")
        print("="*60)
        
        print("\nDatabase Query Performance:")
        for test_name, result in self.results['database_tests'].items():
            print(f"\n{test_name}:")
            print(f"  Average: {result['avg_time_ms']:.2f}ms")
            print(f"  P95: {result['p95_time_ms']:.2f}ms")
            print(f"  P99: {result['p99_time_ms']:.2f}ms")
        
        print("\nRedis Performance:")
        redis_results = self.results['redis_tests']
        print(f"  SET operations avg: {redis_results['set_operations']['avg_time_ms']:.3f}ms")
        print(f"  GET operations avg: {redis_results['get_operations']['avg_time_ms']:.3f}ms")
        print(f"  Pipeline operations avg: {redis_results['pipeline_operations']['avg_time_ms']:.2f}ms")
        
        print("\n" + "="*60)
    
    async def cleanup(self):
        """Cleanup test environment"""
        if self.redis:
            await self.redis.close()
        await self.engine.dispose()


async def main():
    """Run database performance tests"""
    tester = DatabasePerformanceTester()
    try:
        await tester.run_all_tests()
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(main())