"""
Health check system for trading platform services
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import psutil
import aioredis
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.database import get_db
from monitoring.metrics import trading_metrics

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ServiceHealth:
    """Overall health status of a service"""
    service_name: str
    status: HealthStatus
    checks: List[HealthCheckResult]
    overall_response_time: float
    last_updated: datetime

class HealthChecker:
    """Health monitoring system for trading platform"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.check_intervals: Dict[str, int] = {}
        self.running = False
        
    def register_check(
        self,
        name: str,
        check_func: Callable,
        interval: int = 60,
        timeout: int = 30
    ):
        """Register a health check"""
        self.checks[name] = check_func
        self.check_intervals[name] = interval
        logger.info(f"Registered health check: {name} (interval: {interval}s)")
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a single health check"""
        start_time = time.time()
        
        try:
            check_func = self.checks[name]
            result = await check_func()
            
            if isinstance(result, dict):
                status = HealthStatus(result.get('status', 'healthy'))
                message = result.get('message', 'Check passed')
                metadata = result.get('metadata', {})
            else:
                status = HealthStatus.HEALTHY
                message = "Check passed"
                metadata = {}
            
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                name=name,
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                response_time=response_time,
                metadata=metadata
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            
            logger.error(f"Health check {name} failed: {str(e)}")
            
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                metadata={'error': str(e)}
            )
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        tasks = []
        for name in self.checks.keys():
            task = asyncio.create_task(self.run_check(name))
            tasks.append((name, task))
        
        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
                self.results[name] = result
            except Exception as e:
                logger.error(f"Error running health check {name}: {str(e)}")
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check execution failed: {str(e)}",
                    timestamp=datetime.utcnow(),
                    response_time=0.0
                )
        
        return results
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        self.running = True
        logger.info("Starting health monitoring")
        
        while self.running:
            try:
                await self.run_all_checks()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {str(e)}")
                await asyncio.sleep(60)
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.running = False
        logger.info("Stopping health monitoring")
    
    def get_service_health(self, service_name: str) -> ServiceHealth:
        """Get overall health status for a service"""
        start_time = time.time()
        
        relevant_checks = [
            result for name, result in self.results.items()
            if service_name in name or name.startswith(service_name)
        ]
        
        if not relevant_checks:
            return ServiceHealth(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                checks=[],
                overall_response_time=0.0,
                last_updated=datetime.utcnow()
            )
        
        # Determine overall status
        statuses = [check.status for check in relevant_checks]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Calculate average response time
        avg_response_time = sum(check.response_time for check in relevant_checks) / len(relevant_checks)
        
        return ServiceHealth(
            service_name=service_name,
            status=overall_status,
            checks=relevant_checks,
            overall_response_time=avg_response_time,
            last_updated=datetime.utcnow()
        )

# Global health checker instance
health_checker = HealthChecker()

# Health check implementations
async def database_health_check() -> Dict[str, Any]:
    """Check database connectivity and performance"""
    try:
        db = next(get_db())
        start_time = time.time()
        
        # Test basic connectivity
        result = db.execute(text("SELECT 1")).fetchone()
        
        # Test transaction performance
        db.execute(text("SELECT COUNT(*) FROM users"))
        
        response_time = time.time() - start_time
        
        # Check connection pool
        pool_info = db.get_bind().pool.status()
        
        if response_time > 1.0:
            return {
                'status': 'degraded',
                'message': f'Slow database response: {response_time:.2f}s',
                'metadata': {
                    'response_time': response_time,
                    'pool_status': pool_info
                }
            }
        
        return {
            'status': 'healthy',
            'message': 'Database is responsive',
            'metadata': {
                'response_time': response_time,
                'pool_status': pool_info
            }
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}',
            'metadata': {'error': str(e)}
        }

async def redis_health_check() -> Dict[str, Any]:
    """Check Redis connectivity and performance"""
    try:
        redis_url = "redis://localhost:6379"
        redis_client = aioredis.from_url(redis_url)
        
        start_time = time.time()
        
        # Test basic connectivity
        await redis_client.ping()
        
        # Test read/write performance
        test_key = "health_check_test"
        await redis_client.set(test_key, "test_value", ex=60)
        value = await redis_client.get(test_key)
        await redis_client.delete(test_key)
        
        response_time = time.time() - start_time
        
        # Get Redis info
        info = await redis_client.info()
        
        await redis_client.close()
        
        if response_time > 0.5:
            return {
                'status': 'degraded',
                'message': f'Slow Redis response: {response_time:.3f}s',
                'metadata': {
                    'response_time': response_time,
                    'memory_usage': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients')
                }
            }
        
        return {
            'status': 'healthy',
            'message': 'Redis is responsive',
            'metadata': {
                'response_time': response_time,
                'memory_usage': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients')
            }
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Redis connection failed: {str(e)}',
            'metadata': {'error': str(e)}
        }

async def system_resources_check() -> Dict[str, Any]:
    """Check system resource utilization"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Load average (Unix systems)
        try:
            load_avg = psutil.getloadavg()
        except AttributeError:
            load_avg = None
        
        metadata = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory_percent,
            'disk_percent': disk_percent,
            'memory_available_gb': round(memory.available / (1024**3), 2),
            'disk_free_gb': round(disk.free / (1024**3), 2)
        }
        
        if load_avg:
            metadata['load_average'] = load_avg
        
        # Determine status
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            status = 'unhealthy'
            message = 'Critical resource usage detected'
        elif cpu_percent > 75 or memory_percent > 75 or disk_percent > 80:
            status = 'degraded'
            message = 'High resource usage detected'
        else:
            status = 'healthy'
            message = 'System resources are normal'
        
        return {
            'status': status,
            'message': message,
            'metadata': metadata
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Failed to check system resources: {str(e)}',
            'metadata': {'error': str(e)}
        }

async def trading_service_health_check() -> Dict[str, Any]:
    """Check trading service health"""
    try:
        from services.strategy_engine import strategy_engine
        from services.broker_service import broker_service
        
        # Check strategy engine
        active_strategies = len(strategy_engine.active_strategies)
        total_strategies = len(strategy_engine.strategies)
        
        # Check broker connectivity
        broker_status = await broker_service.get_account_info()
        
        metadata = {
            'active_strategies': active_strategies,
            'total_strategies': total_strategies,
            'broker_connected': broker_status.get('status') == 'success'
        }
        
        if not metadata['broker_connected']:
            return {
                'status': 'degraded',
                'message': 'Broker connection issues detected',
                'metadata': metadata
            }
        
        return {
            'status': 'healthy',
            'message': 'Trading service is operational',
            'metadata': metadata
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Trading service check failed: {str(e)}',
            'metadata': {'error': str(e)}
        }

async def market_data_health_check() -> Dict[str, Any]:
    """Check market data service health"""
    try:
        from services.live_market_data import LiveMarketDataService
        
        # Initialize the service
        service = LiveMarketDataService()
        
        # Test basic connectivity to each provider
        provider_status = {}
        
        # Test a sample quote retrieval
        test_symbol = "RELIANCE.NS"  # Indian stock symbol
        
        try:
            quote = await service.get_live_quote(test_symbol)
            if quote and quote.get('symbol'):
                provider_status['quote_service'] = 'healthy'
            else:
                provider_status['quote_service'] = 'degraded'
        except Exception as e:
            provider_status['quote_service'] = 'unhealthy'
        
        # Check rate limiting status
        rate_limit_info = {}
        for provider in ['alpha_vantage', 'polygon', 'yahoo_finance']:
            rate_limiter = service.rate_limiters.get(provider)
            if rate_limiter:
                rate_limit_info[provider] = {
                    'calls_made': getattr(rate_limiter, 'calls_made', 0),
                    'limit': getattr(rate_limiter, 'max_calls', 0)
                }
        
        # Check if market data is flowing
        last_update = getattr(service, 'last_update', None)
        
        if last_update:
            time_since_update = (datetime.utcnow() - last_update).total_seconds()
            
            if time_since_update > 300:  # 5 minutes
                return {
                    'status': 'unhealthy',
                    'message': f'No market data updates for {time_since_update:.0f} seconds',
                    'metadata': {
                        'seconds_since_update': time_since_update,
                        'provider_status': provider_status,
                        'rate_limits': rate_limit_info
                    }
                }
            elif time_since_update > 60:  # 1 minute
                return {
                    'status': 'degraded',
                    'message': f'Delayed market data updates: {time_since_update:.0f} seconds',
                    'metadata': {
                        'seconds_since_update': time_since_update,
                        'provider_status': provider_status,
                        'rate_limits': rate_limit_info
                    }
                }
        
        # Determine overall status
        if any(status == 'unhealthy' for status in provider_status.values()):
            overall_status = 'unhealthy'
            message = 'One or more market data providers are unhealthy'
        elif any(status == 'degraded' for status in provider_status.values()):
            overall_status = 'degraded'
            message = 'Some market data providers are experiencing issues'
        else:
            overall_status = 'healthy'
            message = 'Market data service is operational'
        
        return {
            'status': overall_status,
            'message': message,
            'metadata': {
                'last_update': last_update.isoformat() if last_update else None,
                'provider_status': provider_status,
                'rate_limits': rate_limit_info
            }
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Market data check failed: {str(e)}',
            'metadata': {'error': str(e)}
        }

async def ml_service_health_check() -> Dict[str, Any]:
    """Check ML service health"""
    try:
        from services.ml_service import ml_service
        
        # Check if models are loaded
        loaded_models = getattr(ml_service, 'loaded_models', {})
        
        if not loaded_models:
            return {
                'status': 'degraded',
                'message': 'No ML models loaded',
                'metadata': {'loaded_models': 0}
            }
        
        # Test model inference
        test_result = await ml_service.predict("AAPL")
        
        if test_result and test_result.get('status') == 'success':
            return {
                'status': 'healthy',
                'message': 'ML service is operational',
                'metadata': {
                    'loaded_models': len(loaded_models),
                    'model_names': list(loaded_models.keys())
                }
            }
        else:
            return {
                'status': 'degraded',
                'message': 'ML service responding but predictions failing',
                'metadata': {'loaded_models': len(loaded_models)}
            }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'ML service check failed: {str(e)}',
            'metadata': {'error': str(e)}
        }

# Register all health checks
def initialize_health_checks():
    """Initialize all health checks"""
    health_checker.register_check("database", database_health_check, interval=60)
    health_checker.register_check("redis", redis_health_check, interval=60)
    health_checker.register_check("system_resources", system_resources_check, interval=30)
    health_checker.register_check("trading_service", trading_service_health_check, interval=120)
    health_checker.register_check("market_data", market_data_health_check, interval=60)
    health_checker.register_check("ml_service", ml_service_health_check, interval=180)
    
    logger.info("Health checks initialized")

# Health status aggregator
class HealthStatusAggregator:
    """Aggregate health status across all services"""
    
    @staticmethod
    def get_overall_health() -> Dict[str, Any]:
        """Get overall platform health status"""
        start_time = time.time()
        
        services = [
            'database',
            'redis', 
            'trading_service',
            'market_data',
            'ml_service'
        ]
        
        service_statuses = {}
        overall_status = HealthStatus.HEALTHY
        
        for service in services:
            service_health = health_checker.get_service_health(service)
            service_statuses[service] = {
                'status': service_health.status.value,
                'last_updated': service_health.last_updated.isoformat(),
                'response_time': service_health.overall_response_time,
                'checks': len(service_health.checks)
            }
            
            # Update overall status
            if service_health.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif service_health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        response_time = time.time() - start_time
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'response_time': response_time,
            'services': service_statuses,
            'version': '1.0.0',
            'environment': 'production'
        }