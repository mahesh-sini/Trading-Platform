"""
Centralized logging configuration for the trading platform
"""

import os
import json
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import structlog
from pythonjsonlogger import jsonlogger

class TradingJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for trading platform logs"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add custom fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['service'] = 'trading-platform'
        log_record['environment'] = os.getenv('ENVIRONMENT', 'development')
        log_record['version'] = os.getenv('APP_VERSION', '1.0.0')
        
        # Add context information if available
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        if hasattr(record, 'trade_id'):
            log_record['trade_id'] = record.trade_id
        if hasattr(record, 'strategy_id'):
            log_record['strategy_id'] = record.strategy_id
        if hasattr(record, 'symbol'):
            log_record['symbol'] = record.symbol
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id

class ContextFilter(logging.Filter):
    """Filter to add context information to log records"""
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record):
        # Add context to the record
        for key, value in self.context.items():
            setattr(record, key, value)
        return True

class TradingLogger:
    """Enhanced logger for trading platform with structured logging"""
    
    def __init__(self, name: str = __name__):
        self.logger = structlog.get_logger(name)
        self._context = {}
    
    def bind(self, **kwargs) -> 'TradingLogger':
        """Bind context to logger"""
        new_logger = TradingLogger(self.logger._logger.name)
        new_logger.logger = self.logger.bind(**kwargs)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)
    
    def trade_executed(self, trade_data: Dict[str, Any]):
        """Log trade execution"""
        self.logger.info(
            "Trade executed",
            event_type="trade_executed",
            symbol=trade_data.get('symbol'),
            side=trade_data.get('side'),
            quantity=trade_data.get('quantity'),
            price=trade_data.get('price'),
            trade_id=trade_data.get('trade_id'),
            strategy_id=trade_data.get('strategy_id'),
            value=trade_data.get('value')
        )
    
    def strategy_signal(self, signal_data: Dict[str, Any]):
        """Log strategy signal generation"""
        self.logger.info(
            "Strategy signal generated",
            event_type="strategy_signal",
            strategy_id=signal_data.get('strategy_id'),
            strategy_type=signal_data.get('strategy_type'),
            signal_type=signal_data.get('signal_type'),
            symbol=signal_data.get('symbol'),
            confidence=signal_data.get('confidence'),
            reason=signal_data.get('reason')
        )
    
    def risk_violation(self, violation_data: Dict[str, Any]):
        """Log risk violation"""
        self.logger.warning(
            "Risk violation detected",
            event_type="risk_violation",
            violation_type=violation_data.get('violation_type'),
            symbol=violation_data.get('symbol'),
            user_id=violation_data.get('user_id'),
            current_value=violation_data.get('current_value'),
            limit_value=violation_data.get('limit_value')
        )
    
    def market_data_update(self, data_info: Dict[str, Any]):
        """Log market data update"""
        self.logger.debug(
            "Market data updated",
            event_type="market_data_update",
            symbol=data_info.get('symbol'),
            data_type=data_info.get('data_type'),
            latency=data_info.get('latency'),
            age=data_info.get('age')
        )
    
    def api_request(self, request_info: Dict[str, Any]):
        """Log API request"""
        self.logger.info(
            "API request processed",
            event_type="api_request",
            method=request_info.get('method'),
            endpoint=request_info.get('endpoint'),
            status_code=request_info.get('status_code'),
            duration=request_info.get('duration'),
            user_id=request_info.get('user_id'),
            request_id=request_info.get('request_id')
        )
    
    def system_error(self, error_info: Dict[str, Any]):
        """Log system error"""
        self.logger.error(
            "System error occurred",
            event_type="system_error",
            service=error_info.get('service'),
            error_type=error_info.get('error_type'),
            error_message=error_info.get('error_message'),
            stack_trace=error_info.get('stack_trace')
        )

def setup_logging(config_path: Optional[str] = None, log_level: str = "INFO"):
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Default logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": TradingJSONFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
            },
            "console": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "filters": {
            "context": {
                "()": ContextFilter,
                "context": {
                    "service": "trading-platform",
                    "environment": os.getenv("ENVIRONMENT", "development")
                }
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "console",
                "filters": ["context"],
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "json",
                "filters": ["context"],
                "filename": "logs/trading_platform.log",
                "maxBytes": 50 * 1024 * 1024,  # 50MB
                "backupCount": 10
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filters": ["context"],
                "filename": "logs/trading_platform_errors.log",
                "maxBytes": 50 * 1024 * 1024,  # 50MB
                "backupCount": 10
            },
            "trade_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "json",
                "filters": ["context"],
                "filename": "logs/trades.log",
                "maxBytes": 100 * 1024 * 1024,  # 100MB
                "backupCount": 20
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file", "error_file"],
                "level": log_level,
                "propagate": False
            },
            "trading.trades": {
                "handlers": ["trade_file", "console"],
                "level": "INFO",
                "propagate": False
            },
            "trading.strategies": {
                "handlers": ["file", "console"],
                "level": "INFO",
                "propagate": False
            },
            "trading.market_data": {
                "handlers": ["file"],
                "level": "DEBUG",
                "propagate": False
            },
            "trading.risk": {
                "handlers": ["file", "error_file", "console"],
                "level": "WARNING",
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            },
            "sqlalchemy": {
                "handlers": ["file"],
                "level": "WARNING",
                "propagate": False
            }
        }
    }
    
    # Load custom config if provided
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            custom_config = json.load(f)
            config.update(custom_config)
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Log configuration success
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured successfully with level: {log_level}")

def get_logger(name: str) -> TradingLogger:
    """Get a trading logger instance"""
    return TradingLogger(name)

# Pre-configured loggers for different components
trade_logger = get_logger("trading.trades")
strategy_logger = get_logger("trading.strategies")
market_data_logger = get_logger("trading.market_data")
risk_logger = get_logger("trading.risk")
api_logger = get_logger("trading.api")
db_logger = get_logger("trading.database")
ml_logger = get_logger("trading.ml")

# Log correlation context manager
class LogCorrelation:
    """Context manager for log correlation"""
    
    def __init__(self, correlation_id: str, **context):
        self.correlation_id = correlation_id
        self.context = context
        self.original_context = {}
    
    def __enter__(self):
        # Store original context and set new context
        self.original_context = {
            'correlation_id': self.correlation_id,
            **self.context
        }
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context if needed
        pass

def configure_request_logging():
    """Configure logging for HTTP requests"""
    import uuid
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
    
    class LoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            # Generate request ID
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
            
            # Log request
            start_time = time.time()
            
            with LogCorrelation(request_id, 
                              method=request.method, 
                              url=str(request.url)):
                
                api_logger.info(
                    "Request started",
                    method=request.method,
                    url=str(request.url),
                    request_id=request_id
                )
                
                try:
                    response = await call_next(request)
                    duration = time.time() - start_time
                    
                    api_logger.api_request({
                        'method': request.method,
                        'endpoint': request.url.path,
                        'status_code': response.status_code,
                        'duration': duration,
                        'request_id': request_id
                    })
                    
                    return response
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    api_logger.system_error({
                        'service': 'api',
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'request_id': request_id,
                        'duration': duration
                    })
                    
                    raise
    
    return LoggingMiddleware