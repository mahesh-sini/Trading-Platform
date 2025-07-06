import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import psutil
import json
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from services.database import get_db
from models.system_metrics import SystemMetrics, ServiceStatus
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class MetricThreshold:
    name: str
    warning_threshold: float
    critical_threshold: float
    unit: str = ""
    description: str = ""

@dataclass
class SystemAlert:
    timestamp: datetime
    level: AlertLevel
    service: str
    metric_name: str
    current_value: float
    threshold: float
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class PerformanceMonitor:
    """Monitor system and application performance metrics"""
    
    def __init__(self):
        self.metrics_history: Dict[str, List[Dict[str, Any]]] = {}
        self.active_alerts: List[SystemAlert] = []
        self.thresholds = self._define_default_thresholds()
        self.monitoring_active = False
        
    def _define_default_thresholds(self) -> Dict[str, MetricThreshold]:
        """Define default monitoring thresholds"""
        return {
            "cpu_percent": MetricThreshold(
                name="CPU Usage",
                warning_threshold=70.0,
                critical_threshold=90.0,
                unit="%",
                description="System CPU utilization"
            ),
            "memory_percent": MetricThreshold(
                name="Memory Usage",
                warning_threshold=80.0,
                critical_threshold=95.0,
                unit="%",
                description="System memory utilization"
            ),
            "disk_percent": MetricThreshold(
                name="Disk Usage",
                warning_threshold=85.0,
                critical_threshold=95.0,
                unit="%",
                description="Disk space utilization"
            ),
            "api_response_time": MetricThreshold(
                name="API Response Time",
                warning_threshold=1000.0,
                critical_threshold=5000.0,
                unit="ms",
                description="Average API response time"
            ),
            "database_connections": MetricThreshold(
                name="Database Connections",
                warning_threshold=80.0,
                critical_threshold=95.0,
                unit="count",
                description="Active database connections"
            ),
            "trade_execution_time": MetricThreshold(
                name="Trade Execution Time",
                warning_threshold=50.0,
                critical_threshold=100.0,
                unit="ms",
                description="Time to execute trades"
            ),
            "ml_prediction_time": MetricThreshold(
                name="ML Prediction Time",
                warning_threshold=200.0,
                critical_threshold=500.0,
                unit="ms",
                description="Time to generate ML predictions"
            )
        }
    
    async def start_monitoring(self):
        """Start continuous monitoring"""
        self.monitoring_active = True
        logger.info("Performance monitoring started")
        
        # Start monitoring tasks
        monitoring_tasks = [
            asyncio.create_task(self._monitor_system_metrics()),
            asyncio.create_task(self._monitor_application_metrics()),
            asyncio.create_task(self._process_alerts()),
            asyncio.create_task(self._cleanup_old_metrics())
        ]
        
        try:
            await asyncio.gather(*monitoring_tasks)
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
        finally:
            self.monitoring_active = False
    
    async def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring_active = False
        logger.info("Performance monitoring stopped")
    
    async def _monitor_system_metrics(self):
        """Monitor system-level metrics"""
        while self.monitoring_active:
            try:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                await self._record_metric("cpu_percent", cpu_percent)
                
                # Memory metrics
                memory = psutil.virtual_memory()
                await self._record_metric("memory_percent", memory.percent)
                await self._record_metric("memory_available_gb", memory.available / (1024**3))
                
                # Disk metrics
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                await self._record_metric("disk_percent", disk_percent)
                await self._record_metric("disk_free_gb", disk.free / (1024**3))
                
                # Network metrics
                network = psutil.net_io_counters()
                await self._record_metric("network_bytes_sent", network.bytes_sent)
                await self._record_metric("network_bytes_recv", network.bytes_recv)
                
                # Process metrics
                process = psutil.Process()
                await self._record_metric("process_memory_mb", process.memory_info().rss / (1024**2))
                await self._record_metric("process_cpu_percent", process.cpu_percent())
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring system metrics: {str(e)}")
                await asyncio.sleep(30)
    
    async def _monitor_application_metrics(self):
        """Monitor application-specific metrics"""
        while self.monitoring_active:
            try:
                # Database connection pool metrics
                db_metrics = await self._get_database_metrics()
                for metric_name, value in db_metrics.items():
                    await self._record_metric(metric_name, value)
                
                # Trading service metrics
                trading_metrics = await self._get_trading_metrics()
                for metric_name, value in trading_metrics.items():
                    await self._record_metric(metric_name, value)
                
                # ML service metrics
                ml_metrics = await self._get_ml_metrics()
                for metric_name, value in ml_metrics.items():
                    await self._record_metric(metric_name, value)
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Error monitoring application metrics: {str(e)}")
                await asyncio.sleep(60)
    
    async def _record_metric(self, metric_name: str, value: float):
        """Record a metric value and check thresholds"""
        timestamp = datetime.now()
        
        # Store metric
        if metric_name not in self.metrics_history:
            self.metrics_history[metric_name] = []
        
        self.metrics_history[metric_name].append({
            "timestamp": timestamp,
            "value": value
        })
        
        # Check thresholds
        if metric_name in self.thresholds:
            await self._check_threshold(metric_name, value, timestamp)
    
    async def _check_threshold(self, metric_name: str, value: float, timestamp: datetime):
        """Check if metric exceeds thresholds"""
        threshold = self.thresholds[metric_name]
        
        if value >= threshold.critical_threshold:
            alert = SystemAlert(
                timestamp=timestamp,
                level=AlertLevel.CRITICAL,
                service="system",
                metric_name=metric_name,
                current_value=value,
                threshold=threshold.critical_threshold,
                message=f"{threshold.name} is critically high: {value}{threshold.unit} (threshold: {threshold.critical_threshold}{threshold.unit})"
            )
            await self._handle_alert(alert)
            
        elif value >= threshold.warning_threshold:
            alert = SystemAlert(
                timestamp=timestamp,
                level=AlertLevel.WARNING,
                service="system",
                metric_name=metric_name,
                current_value=value,
                threshold=threshold.warning_threshold,
                message=f"{threshold.name} is high: {value}{threshold.unit} (threshold: {threshold.warning_threshold}{threshold.unit})"
            )
            await self._handle_alert(alert)
    
    async def _handle_alert(self, alert: SystemAlert):
        """Handle system alerts"""
        # Check if we already have a recent alert for this metric
        recent_alerts = [
            a for a in self.active_alerts 
            if a.metric_name == alert.metric_name 
            and a.level == alert.level
            and (alert.timestamp - a.timestamp).total_seconds() < 300  # 5 minutes
        ]
        
        if not recent_alerts:
            self.active_alerts.append(alert)
            logger.warning(f"ALERT: {alert.message}")
            
            # Send notification
            await notification_service.send_alert(alert)
            
            # Store in database
            await self._store_alert(alert)
    
    async def _process_alerts(self):
        """Process and manage active alerts"""
        while self.monitoring_active:
            try:
                # Remove resolved alerts
                current_time = datetime.now()
                self.active_alerts = [
                    alert for alert in self.active_alerts
                    if (current_time - alert.timestamp).total_seconds() < 3600  # Keep for 1 hour
                ]
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error processing alerts: {str(e)}")
                await asyncio.sleep(300)
    
    async def _cleanup_old_metrics(self):
        """Clean up old metric data"""
        while self.monitoring_active:
            try:
                cutoff_time = datetime.now() - timedelta(hours=24)  # Keep 24 hours
                
                for metric_name in list(self.metrics_history.keys()):
                    self.metrics_history[metric_name] = [
                        metric for metric in self.metrics_history[metric_name]
                        if metric["timestamp"] > cutoff_time
                    ]
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error(f"Error cleaning up metrics: {str(e)}")
                await asyncio.sleep(3600)
    
    async def _get_database_metrics(self) -> Dict[str, float]:
        """Get database performance metrics"""
        try:
            # This would integrate with database monitoring
            return {
                "database_connections": 10.0,  # Mock value
                "database_query_time": 25.0,    # Mock value
                "database_lock_waits": 0.0       # Mock value
            }
        except Exception as e:
            logger.error(f"Error getting database metrics: {str(e)}")
            return {}
    
    async def _get_trading_metrics(self) -> Dict[str, float]:
        """Get trading service metrics"""
        try:
            # This would integrate with trading service
            return {
                "trade_execution_time": 35.0,    # Mock value
                "order_fill_rate": 98.5,         # Mock value
                "active_positions": 15.0         # Mock value
            }
        except Exception as e:
            logger.error(f"Error getting trading metrics: {str(e)}")
            return {}
    
    async def _get_ml_metrics(self) -> Dict[str, float]:
        """Get ML service metrics"""
        try:
            # This would integrate with ML service
            return {
                "ml_prediction_time": 150.0,     # Mock value
                "model_accuracy": 87.5,          # Mock value
                "prediction_requests": 42.0      # Mock value
            }
        except Exception as e:
            logger.error(f"Error getting ML metrics: {str(e)}")
            return {}
    
    async def _store_alert(self, alert: SystemAlert):
        """Store alert in database"""
        try:
            # This would store alert in database
            logger.info(f"Alert stored: {alert.message}")
        except Exception as e:
            logger.error(f"Error storing alert: {str(e)}")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics"""
        summary = {}
        
        for metric_name, history in self.metrics_history.items():
            if history:
                latest = history[-1]
                recent_values = [m["value"] for m in history[-10:]]  # Last 10 values
                
                summary[metric_name] = {
                    "current_value": latest["value"],
                    "timestamp": latest["timestamp"].isoformat(),
                    "average_recent": sum(recent_values) / len(recent_values),
                    "min_recent": min(recent_values),
                    "max_recent": max(recent_values),
                    "data_points": len(history)
                }
        
        return summary
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get current active alerts"""
        return [
            {
                "timestamp": alert.timestamp.isoformat(),
                "level": alert.level.value,
                "service": alert.service,
                "metric_name": alert.metric_name,
                "current_value": alert.current_value,
                "threshold": alert.threshold,
                "message": alert.message,
                "metadata": alert.metadata
            }
            for alert in self.active_alerts
        ]

class LoggingManager:
    """Enhanced logging management with structured logging"""
    
    def __init__(self):
        self.log_aggregator = {}
        self.setup_structured_logging()
    
    def setup_structured_logging(self):
        """Setup structured logging with JSON formatter"""
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add extra fields if present
                if hasattr(record, 'user_id'):
                    log_entry['user_id'] = record.user_id
                if hasattr(record, 'trade_id'):
                    log_entry['trade_id'] = record.trade_id
                if hasattr(record, 'strategy_id'):
                    log_entry['strategy_id'] = record.strategy_id
                if hasattr(record, 'request_id'):
                    log_entry['request_id'] = record.request_id
                
                return json.dumps(log_entry)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # File handler for structured logs
        file_handler = logging.FileHandler('/app/logs/application.jsonl')
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        root_logger.addHandler(console_handler)
    
    @asynccontextmanager
    async def log_context(self, **context):
        """Context manager for adding context to logs"""
        # This would add context to all logs within the context
        yield context

class HealthChecker:
    """Service health checking"""
    
    def __init__(self):
        self.services = {
            "database": self._check_database,
            "redis": self._check_redis,
            "trading_service": self._check_trading_service,
            "ml_service": self._check_ml_service,
            "data_service": self._check_data_service
        }
    
    async def check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all services"""
        results = {}
        
        for service_name, check_func in self.services.items():
            try:
                start_time = time.time()
                status = await check_func()
                response_time = (time.time() - start_time) * 1000
                
                results[service_name] = {
                    "status": "healthy" if status else "unhealthy",
                    "response_time_ms": response_time,
                    "timestamp": datetime.now().isoformat(),
                    "details": status if isinstance(status, dict) else {}
                }
            except Exception as e:
                results[service_name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        return results
    
    async def _check_database(self) -> bool:
        """Check database connectivity"""
        try:
            # Simple database connectivity check
            return True  # Mock implementation
        except Exception:
            return False
    
    async def _check_redis(self) -> bool:
        """Check Redis connectivity"""
        try:
            # Redis connectivity check
            return True  # Mock implementation
        except Exception:
            return False
    
    async def _check_trading_service(self) -> bool:
        """Check trading service"""
        try:
            # Trading service health check
            return True  # Mock implementation
        except Exception:
            return False
    
    async def _check_ml_service(self) -> bool:
        """Check ML service"""
        try:
            # ML service health check
            return True  # Mock implementation
        except Exception:
            return False
    
    async def _check_data_service(self) -> bool:
        """Check data service"""
        try:
            # Data service health check
            return True  # Mock implementation
        except Exception:
            return False

# Global instances
performance_monitor = PerformanceMonitor()
logging_manager = LoggingManager()
health_checker = HealthChecker()