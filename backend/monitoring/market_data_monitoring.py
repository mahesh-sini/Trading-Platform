"""
Enhanced monitoring integration for live market data service
"""

import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

from monitoring.metrics import trading_metrics
from monitoring.logging_config import market_data_logger
from monitoring.health_checks import health_checker

logger = logging.getLogger(__name__)

class MarketDataMonitor:
    """Enhanced monitoring for market data service"""
    
    def __init__(self, market_data_service):
        self.service = market_data_service
        self.monitoring_tasks: List[asyncio.Task] = []
        self.metrics_cache = {}
        self.last_health_check = None
        
    async def start_monitoring(self):
        """Start all monitoring tasks"""
        try:
            # Start metrics collection task
            self.monitoring_tasks.append(
                asyncio.create_task(self._collect_metrics_periodically())
            )
            
            # Start health monitoring task
            self.monitoring_tasks.append(
                asyncio.create_task(self._monitor_health_periodically())
            )
            
            # Start rate limit monitoring
            self.monitoring_tasks.append(
                asyncio.create_task(self._monitor_rate_limits())
            )
            
            logger.info("Market data monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start market data monitoring: {e}")
            
    async def stop_monitoring(self):
        """Stop all monitoring tasks"""
        try:
            for task in self.monitoring_tasks:
                task.cancel()
                
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            self.monitoring_tasks.clear()
            
            logger.info("Market data monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping market data monitoring: {e}")
    
    async def _collect_metrics_periodically(self):
        """Collect and update metrics every 30 seconds"""
        while True:
            try:
                await self._collect_service_metrics()
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_health_periodically(self):
        """Monitor service health every 60 seconds"""
        while True:
            try:
                await self._check_service_health()
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(120)
    
    async def _monitor_rate_limits(self):
        """Monitor rate limits every 10 seconds"""
        while True:
            try:
                await self._update_rate_limit_metrics()
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rate limit monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _collect_service_metrics(self):
        """Collect various service metrics"""
        try:
            # Update subscription metrics
            subscriptions = getattr(self.service, 'subscribed_symbols', set())
            for symbol in subscriptions:
                trading_metrics.update_live_subscription('live_service', symbol, True)
            
            # Update WebSocket connection metrics
            ws_connections = getattr(self.service, 'websocket_connections', {})
            trading_metrics.websocket_connections.labels(
                connection_type='market_data'
            ).set(len(ws_connections))
            
            # Log service status
            market_data_logger.info(
                "Market data service metrics collected",
                active_subscriptions=len(subscriptions),
                websocket_connections=len(ws_connections)
            )
            
        except Exception as e:
            logger.error(f"Error collecting service metrics: {e}")
    
    async def _check_service_health(self):
        """Perform health checks on the service"""
        try:
            # Check if session is active
            session_healthy = (
                self.service.session is not None and 
                not self.service.session.closed
            )
            
            # Check provider connectivity (sample test)
            connectivity_test = await self._test_provider_connectivity()
            
            # Update health status
            if session_healthy and connectivity_test:
                status = 'healthy'
                message = 'Market data service is operational'
            elif session_healthy or connectivity_test:
                status = 'degraded'
                message = 'Market data service has partial issues'
            else:
                status = 'unhealthy'
                message = 'Market data service is not operational'
            
            self.last_health_check = {
                'status': status,
                'message': message,
                'timestamp': datetime.utcnow(),
                'session_healthy': session_healthy,
                'connectivity_test': connectivity_test
            }
            
            market_data_logger.info(
                f"Health check completed: {status}",
                health_status=status,
                session_healthy=session_healthy,
                connectivity_test=connectivity_test
            )
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            self.last_health_check = {
                'status': 'unhealthy',
                'message': f'Health check failed: {str(e)}',
                'timestamp': datetime.utcnow(),
                'error': str(e)
            }
    
    async def _test_provider_connectivity(self) -> bool:
        """Test connectivity to market data providers"""
        try:
            # Quick test with a common symbol
            test_quote = await self.service.get_live_quote('RELIANCE', 'NSE')
            return test_quote is not None
            
        except Exception as e:
            logger.warning(f"Provider connectivity test failed: {e}")
            return False
    
    async def _update_rate_limit_metrics(self):
        """Update rate limit metrics for all providers"""
        try:
            rate_limits = getattr(self.service, 'rate_limits', {})
            
            for provider, limit_data in rate_limits.items():
                if isinstance(limit_data, dict):
                    requests = limit_data.get('requests', [])
                    max_requests = self.service.providers.get(provider, {}).get('rate_limit', 0)
                    
                    # Calculate remaining requests
                    current_time = datetime.now()
                    minute_ago = current_time - timedelta(minutes=1)
                    recent_requests = [r for r in requests if r > minute_ago]
                    remaining = max(0, max_requests - len(recent_requests))
                    
                    trading_metrics.update_provider_rate_limit(provider, remaining)
            
        except Exception as e:
            logger.error(f"Error updating rate limit metrics: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        return {
            'monitoring_active': len(self.monitoring_tasks) > 0,
            'active_tasks': len(self.monitoring_tasks),
            'last_health_check': self.last_health_check,
            'metrics_cache': self.metrics_cache
        }

# Enhanced health check specifically for live market data
async def enhanced_market_data_health_check() -> Dict[str, Any]:
    """Enhanced health check for live market data service"""
    try:
        from services.live_market_data import LiveMarketDataService
        
        service = LiveMarketDataService()
        monitor = MarketDataMonitor(service)
        
        # Perform comprehensive health check
        start_time = time.time()
        
        # Test service initialization
        await service.ensure_session()
        
        # Test provider connectivity
        test_results = {}
        test_symbols = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS']
        
        for symbol in test_symbols:
            try:
                quote = await service.get_live_quote(symbol.replace('.NS', ''))
                test_results[symbol] = 'success' if quote else 'no_data'
            except Exception as e:
                test_results[symbol] = f'error: {str(e)}'
        
        # Check rate limit status
        rate_limit_status = {}
        for provider in service.providers:
            rate_limiter = service.rate_limits.get(provider, {})
            if isinstance(rate_limiter, dict):
                requests = rate_limiter.get('requests', [])
                rate_limit_status[provider] = {
                    'recent_requests': len(requests),
                    'limit': service.providers[provider].get('rate_limit', 0)
                }
        
        health_duration = time.time() - start_time
        
        # Determine overall status
        successful_tests = sum(1 for result in test_results.values() if result == 'success')
        total_tests = len(test_results)
        
        if successful_tests == total_tests:
            status = 'healthy'
            message = 'All market data providers are responding'
        elif successful_tests > 0:
            status = 'degraded'
            message = f'{successful_tests}/{total_tests} providers responding'
        else:
            status = 'unhealthy'
            message = 'No market data providers are responding'
        
        await service.close()
        
        return {
            'status': status,
            'message': message,
            'metadata': {
                'health_check_duration': health_duration,
                'provider_tests': test_results,
                'rate_limit_status': rate_limit_status,
                'successful_providers': successful_tests,
                'total_providers': total_tests
            }
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Enhanced health check failed: {str(e)}',
            'metadata': {'error': str(e)}
        }

# Register the enhanced health check
def register_enhanced_market_data_monitoring():
    """Register enhanced monitoring for market data"""
    health_checker.register_check(
        "enhanced_market_data", 
        enhanced_market_data_health_check, 
        interval=120,  # Every 2 minutes
        timeout=60
    )
    logger.info("Enhanced market data monitoring registered")