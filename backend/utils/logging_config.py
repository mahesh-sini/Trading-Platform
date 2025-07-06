import logging
import logging.config
import os
from datetime import datetime
import structlog

def setup_logging():
    """Configure structured logging with different levels for different environments"""
    
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    environment = os.getenv("ENVIRONMENT", "development")
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if environment == "production":
        # JSON logging for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty printing for development
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d]: %(message)s"
            },
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
            },
        },
        "handlers": {
            "default": {
                "level": log_level,
                "formatter": "json" if environment == "production" else "detailed",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "level": log_level,
                "formatter": "json" if environment == "production" else "detailed",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": "logs/trading_platform.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "": {
                "handlers": ["default", "file"] if environment == "production" else ["default"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "sqlalchemy": {
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": False,
            },
            "alembic": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Set up application logger
    logger = structlog.get_logger()
    logger.info("Logging configured", environment=environment, log_level=log_level)

def get_logger(name: str):
    """Get a structured logger instance"""
    return structlog.get_logger(name)