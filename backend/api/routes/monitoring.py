"""
Monitoring and observability API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from services.database import get_db
from models.user import User
from services.auth_service import get_current_user, get_current_admin_user
from monitoring.metrics import trading_metrics
from monitoring.health_checks import health_checker, HealthStatusAggregator
from monitoring.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        overall_health = HealthStatusAggregator.get_overall_health()
        
        if overall_health['status'] == 'unhealthy':
            return Response(
                content=overall_health,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                media_type="application/json"
            )
        elif overall_health['status'] == 'degraded':
            return Response(
                content=overall_health,
                status_code=status.HTTP_200_OK,
                media_type="application/json"
            )
        else:
            return overall_health
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check system failure"
        )

@router.get("/health/detailed")
async def detailed_health_check(
    current_user: User = Depends(get_current_admin_user)
):
    """Detailed health check with all service statuses"""
    try:
        # Run all health checks
        check_results = await health_checker.run_all_checks()
        
        # Get service health summaries
        services = ['database', 'redis', 'trading_service', 'market_data', 'ml_service']
        service_health = {}
        
        for service in services:
            service_health[service] = health_checker.get_service_health(service).__dict__
        
        overall_health = HealthStatusAggregator.get_overall_health()
        
        return {
            "overall": overall_health,
            "services": service_health,
            "individual_checks": {
                name: {
                    "name": result.name,
                    "status": result.status.value,
                    "message": result.message,
                    "timestamp": result.timestamp.isoformat(),
                    "response_time": result.response_time,
                    "metadata": result.metadata
                }
                for name, result in check_results.items()
            }
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check system failure"
        )

@router.get("/health/readiness")
async def readiness_check():
    """Kubernetes readiness probe endpoint"""
    try:
        # Check critical services only
        critical_checks = ['database', 'trading_service']
        
        for service in critical_checks:
            service_health = health_checker.get_service_health(service)
            if service_health.status.value == 'unhealthy':
                return Response(
                    content={"status": "not_ready", "reason": f"{service} is unhealthy"},
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    media_type="application/json"
                )
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return Response(
            content={"status": "not_ready", "reason": "readiness check failed"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )

@router.get("/health/liveness")
async def liveness_check():
    """Kubernetes liveness probe endpoint"""
    try:
        # Simple check that the application is running
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Liveness check failed: {str(e)}")
        return Response(
            content={"status": "dead", "reason": "liveness check failed"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            media_type="application/json"
        )

@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = trading_metrics.get_metrics()
        return Response(
            content=metrics_data,
            media_type=trading_metrics.get_content_type()
        )
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Metrics collection failed"
        )

@router.get("/metrics/trading")
async def trading_metrics_summary(
    current_user: User = Depends(get_current_user)
):
    """Get trading-specific metrics summary"""
    try:
        # This would typically aggregate from Prometheus
        # For now, return mock data structure
        return {
            "trades": {
                "total_today": 45,
                "successful_today": 42,
                "failed_today": 3,
                "total_value_today": 125000.0
            },
            "strategies": {
                "active_count": 8,
                "total_signals_today": 23,
                "execution_rate": 0.87
            },
            "portfolio": {
                "total_value": 250000.0,
                "daily_pnl": 1250.0,
                "unrealized_pnl": 3200.0
            },
            "market_data": {
                "symbols_tracked": 15,
                "updates_per_minute": 120,
                "average_latency_ms": 45
            }
        }
        
    except Exception as e:
        logger.error(f"Trading metrics summary failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trading metrics"
        )

@router.get("/logs/search")
async def search_logs(
    query: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    level: Optional[str] = None,
    service: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user)
):
    """Search application logs"""
    try:
        # This would integrate with a log aggregation system like ELK stack
        # For now, return mock log data
        
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        # Mock log entries
        logs = [
            {
                "timestamp": "2024-01-15T10:30:45.123Z",
                "level": "INFO",
                "service": "trading-service",
                "message": "Trade executed successfully",
                "metadata": {
                    "trade_id": "trade_123",
                    "symbol": "AAPL",
                    "quantity": 100,
                    "price": 150.25
                }
            },
            {
                "timestamp": "2024-01-15T10:29:12.456Z",
                "level": "WARNING",
                "service": "risk-service",
                "message": "Position size approaching limit",
                "metadata": {
                    "user_id": "user_456",
                    "symbol": "TSLA",
                    "current_position": 0.08,
                    "limit": 0.10
                }
            }
        ]
        
        # Filter by parameters
        filtered_logs = []
        for log in logs:
            if level and log["level"] != level.upper():
                continue
            if service and log["service"] != service:
                continue
            if query and query.lower() not in log["message"].lower():
                continue
            filtered_logs.append(log)
        
        return {
            "query": query,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_results": len(filtered_logs),
            "results": filtered_logs[:limit]
        }
        
    except Exception as e:
        logger.error(f"Log search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Log search failed"
        )

@router.get("/alerts")
async def get_active_alerts(
    current_user: User = Depends(get_current_admin_user)
):
    """Get active system alerts"""
    try:
        # Check for various alert conditions
        alerts = []
        
        # Check health status for alerts
        overall_health = HealthStatusAggregator.get_overall_health()
        
        if overall_health['status'] == 'unhealthy':
            alerts.append({
                "id": "system_unhealthy",
                "severity": "critical",
                "title": "System Health Critical",
                "description": "One or more critical services are unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": [
                    service for service, status in overall_health['services'].items()
                    if status['status'] == 'unhealthy'
                ]
            })
        elif overall_health['status'] == 'degraded':
            alerts.append({
                "id": "system_degraded",
                "severity": "warning",
                "title": "System Performance Degraded",
                "description": "Some services are experiencing issues",
                "timestamp": datetime.utcnow().isoformat(),
                "services": [
                    service for service, status in overall_health['services'].items()
                    if status['status'] == 'degraded'
                ]
            })
        
        # Add other alert conditions here
        # - High error rates
        # - Resource exhaustion
        # - Trading anomalies
        # - Security events
        
        return {
            "active_alerts": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        logger.error(f"Get alerts failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get alerts"
        )

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Acknowledge an alert"""
    try:
        # In a real system, this would update the alert status in a database
        logger.info(
            "Alert acknowledged",
            alert_id=alert_id,
            user_id=current_user.id,
            timestamp=datetime.utcnow().isoformat()
        )
        
        return {
            "alert_id": alert_id,
            "acknowledged_by": current_user.id,
            "acknowledged_at": datetime.utcnow().isoformat(),
            "status": "acknowledged"
        }
        
    except Exception as e:
        logger.error(f"Alert acknowledgment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge alert"
        )

@router.get("/system/info")
async def system_info(
    current_user: User = Depends(get_current_admin_user)
):
    """Get system information"""
    try:
        import psutil
        import platform
        
        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "resources": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_total_gb": round(psutil.disk_usage('/').total / (1024**3), 2)
            },
            "application": {
                "version": "1.0.0",
                "environment": "production",
                "startup_time": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"System info failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system information"
        )

@router.get("/performance/dashboard")
async def performance_dashboard(
    time_range: str = "1h",  # 1h, 6h, 24h, 7d
    current_user: User = Depends(get_current_user)
):
    """Get performance dashboard data"""
    try:
        # This would typically query a time-series database
        # For now, return mock dashboard data
        
        return {
            "time_range": time_range,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "api_latency": {
                    "p50": 45.2,
                    "p95": 120.5,
                    "p99": 250.1
                },
                "trade_execution": {
                    "success_rate": 98.5,
                    "average_latency_ms": 35.2,
                    "volume_today": 1250000.0
                },
                "strategy_performance": {
                    "active_strategies": 8,
                    "avg_sharpe_ratio": 1.45,
                    "total_signals": 156
                },
                "system_resources": {
                    "cpu_usage": 35.2,
                    "memory_usage": 62.1,
                    "disk_usage": 45.8
                }
            },
            "trends": {
                "api_requests_per_minute": [120, 135, 128, 145, 132],
                "trades_per_hour": [12, 8, 15, 23, 18],
                "error_rate_percentage": [0.5, 0.3, 0.8, 0.2, 0.1]
            }
        }
        
    except Exception as e:
        logger.error(f"Performance dashboard failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performance dashboard data"
        )