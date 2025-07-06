#!/usr/bin/env python3
"""
Production Monitoring Setup Script
Sets up comprehensive monitoring for the AI Trading Platform
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from monitoring.metrics import trading_metrics, start_metrics_server
from monitoring.logging_config import setup_logging, get_logger
from monitoring.health_checks import initialize_health_checks, health_checker
from monitoring.market_data_monitoring import register_enhanced_market_data_monitoring

logger = logging.getLogger(__name__)

class MonitoringSetup:
    """Comprehensive monitoring setup for trading platform"""
    
    def __init__(self):
        self.metrics_port = int(os.getenv('METRICS_PORT', 8001))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.environment = os.getenv('ENVIRONMENT', 'production')
        
    def setup_logging(self):
        """Initialize logging configuration"""
        try:
            setup_logging(log_level=self.log_level)
            logger.info(f"Logging initialized with level: {self.log_level}")
            
            # Set application info
            trading_metrics.set_app_info({
                'version': '1.0.0',
                'environment': self.environment,
                'service': 'ai-trading-platform'
            })
            
            return True
            
        except Exception as e:
            print(f"Failed to setup logging: {e}")
            return False
    
    def setup_metrics(self):
        """Initialize Prometheus metrics server"""
        try:
            start_metrics_server(self.metrics_port)
            logger.info(f"Metrics server started on port {self.metrics_port}")
            
            # Log metrics endpoint info
            logger.info(f"Metrics available at: http://localhost:{self.metrics_port}/metrics")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup metrics server: {e}")
            return False
    
    def setup_health_checks(self):
        """Initialize health monitoring"""
        try:
            # Initialize standard health checks
            initialize_health_checks()
            
            # Register enhanced market data monitoring
            register_enhanced_market_data_monitoring()
            
            logger.info("Health checks initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup health checks: {e}")
            return False
    
    async def start_monitoring(self):
        """Start all monitoring services"""
        try:
            # Start health monitoring
            monitoring_task = asyncio.create_task(health_checker.start_monitoring())
            
            logger.info("All monitoring services started successfully")
            
            # Keep monitoring running
            await monitoring_task
            
        except KeyboardInterrupt:
            logger.info("Monitoring shutdown requested")
            health_checker.stop_monitoring()
            
        except Exception as e:
            logger.error(f"Error in monitoring services: {e}")
            health_checker.stop_monitoring()
    
    def verify_setup(self):
        """Verify monitoring setup"""
        verification_results = {
            'logging': False,
            'metrics': False,
            'health_checks': False,
            'alerting_rules': False
        }
        
        try:
            # Check logging
            test_logger = get_logger('test')
            test_logger.info("Logging verification test")
            verification_results['logging'] = True
            logger.info("✅ Logging verification passed")
            
        except Exception as e:
            logger.error(f"❌ Logging verification failed: {e}")
        
        try:
            # Check metrics
            metrics_output = trading_metrics.get_metrics()
            if metrics_output:
                verification_results['metrics'] = True
                logger.info("✅ Metrics verification passed")
            else:
                logger.error("❌ Metrics verification failed: No metrics output")
                
        except Exception as e:
            logger.error(f"❌ Metrics verification failed: {e}")
        
        try:
            # Check health checks
            if len(health_checker.checks) > 0:
                verification_results['health_checks'] = True
                logger.info(f"✅ Health checks verification passed ({len(health_checker.checks)} checks registered)")
            else:
                logger.error("❌ Health checks verification failed: No checks registered")
                
        except Exception as e:
            logger.error(f"❌ Health checks verification failed: {e}")
        
        try:
            # Check alerting rules file
            alerting_rules_path = Path(__file__).parent / "backend" / "monitoring" / "alerting_rules.yml"
            if alerting_rules_path.exists():
                verification_results['alerting_rules'] = True
                logger.info("✅ Alerting rules verification passed")
            else:
                logger.error("❌ Alerting rules verification failed: File not found")
                
        except Exception as e:
            logger.error(f"❌ Alerting rules verification failed: {e}")
        
        # Summary
        passed = sum(verification_results.values())
        total = len(verification_results)
        
        if passed == total:
            logger.info(f"🎉 All monitoring components verified successfully ({passed}/{total})")
            return True
        else:
            logger.warning(f"⚠️  Monitoring verification completed with issues ({passed}/{total} passed)")
            return False
    
    def print_monitoring_info(self):
        """Print monitoring setup information"""
        print("\n" + "="*60)
        print("🚀 AI Trading Platform - Production Monitoring Setup")
        print("="*60)
        print(f"Environment: {self.environment}")
        print(f"Log Level: {self.log_level}")
        print(f"Metrics Port: {self.metrics_port}")
        print("\n📊 Monitoring Endpoints:")
        print(f"  • Metrics: http://localhost:{self.metrics_port}/metrics")
        print(f"  • Health: http://localhost:8000/health (when API server is running)")
        print("\n📁 Monitoring Files:")
        print(f"  • Logs: backend/logs/")
        print(f"  • Metrics Config: backend/monitoring/metrics.py")
        print(f"  • Health Checks: backend/monitoring/health_checks.py")
        print(f"  • Alerting Rules: backend/monitoring/alerting_rules.yml")
        print("\n🔧 Key Metrics:")
        print("  • trading_trades_total - Total trades executed")
        print("  • trading_market_data_latency_seconds - Market data latency")
        print("  • trading_provider_errors_total - Provider error counts")
        print("  • trading_api_request_duration_seconds - API response times")
        print("  • trading_ml_predictions_total - ML prediction counts")
        print("\n⚡ Alerting Rules:")
        print("  • Market data provider failures")
        print("  • High latency alerts")
        print("  • Rate limit warnings")
        print("  • System resource alerts")
        print("  • Trading performance alerts")
        print("="*60)

async def main():
    """Main monitoring setup function"""
    setup = MonitoringSetup()
    
    # Print setup information
    setup.print_monitoring_info()
    
    print("\n🔧 Setting up monitoring components...")
    
    # Setup logging first
    if not setup.setup_logging():
        print("❌ Failed to setup logging. Exiting.")
        return 1
    
    # Setup metrics
    if not setup.setup_metrics():
        logger.error("Failed to setup metrics. Continuing with limited monitoring.")
    
    # Setup health checks
    if not setup.setup_health_checks():
        logger.error("Failed to setup health checks. Continuing with limited monitoring.")
    
    # Verify setup
    logger.info("Verifying monitoring setup...")
    verification_passed = setup.verify_setup()
    
    if verification_passed:
        logger.info("🎉 Monitoring setup completed successfully!")
        print("\n✅ Monitoring is now active and ready for production use!")
        print("📊 Check the metrics endpoint and logs to verify data collection.")
        
        # Option to start monitoring services
        if '--start' in sys.argv:
            print("\n🚀 Starting monitoring services...")
            await setup.start_monitoring()
        else:
            print("\n💡 Run with --start flag to keep monitoring services running")
            print("   Example: python setup_monitoring.py --start")
    else:
        logger.warning("⚠️  Monitoring setup completed with some issues.")
        print("\n⚠️  Some monitoring components may not work correctly.")
        print("📋 Check the logs above for specific issues to resolve.")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error in monitoring setup: {e}")
        sys.exit(1)