"""
System Setup Service
Initializes system features and default configurations
"""

from sqlalchemy.orm import Session
from ..models.system_config import SystemFeatureConfig, APIProviderEnum
from ..models.admin import Admin, AdminRoleEnum
from ..services.admin_auth_service import AdminAuthService
from ..services.database import get_db
from datetime import datetime
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

auth_service = AdminAuthService(secret_key="system-setup-key")


class SystemSetupService:
    """Service for setting up initial system configuration"""
    
    @staticmethod
    def create_default_features(db: Session):
        """Create default system features if they don't exist"""
        
        default_features = [
            {
                "feature_name": "live_market_data",
                "display_name": "Live Market Data",
                "description": "Real-time market data feeds for charts and price tracking",
                "category": "market_data",
                "priority": 10,
                "required_apis": ["alpha_vantage", "polygon", "yahoo_finance"],
                "optional_apis": ["finnhub", "iex_cloud"],
                "config_schema": {
                    "update_interval_seconds": {"type": "integer", "default": 5, "min": 1, "max": 60},
                    "symbols_limit": {"type": "integer", "default": 100, "min": 10, "max": 1000},
                    "enable_websocket": {"type": "boolean", "default": True}
                },
                "config_values": {
                    "update_interval_seconds": 5,
                    "symbols_limit": 100,
                    "enable_websocket": True
                }
            },
            {
                "feature_name": "historical_data",
                "display_name": "Historical Market Data",
                "description": "Historical price data for backtesting and analysis",
                "category": "market_data",
                "priority": 9,
                "required_apis": ["alpha_vantage", "polygon"],
                "optional_apis": ["yahoo_finance", "quandl"],
                "config_schema": {
                    "data_retention_days": {"type": "integer", "default": 365, "min": 30, "max": 3650},
                    "supported_timeframes": {"type": "array", "default": ["1m", "5m", "15m", "1h", "1d"]},
                    "enable_intraday": {"type": "boolean", "default": True}
                },
                "config_values": {
                    "data_retention_days": 365,
                    "supported_timeframes": ["1m", "5m", "15m", "1h", "1d"],
                    "enable_intraday": True
                }
            },
            {
                "feature_name": "indian_market_data",
                "display_name": "Indian Market Data",
                "description": "NSE/BSE live and historical data feeds",
                "category": "market_data",
                "priority": 10,
                "required_apis": ["nse_official"],
                "optional_apis": ["bse_official", "economic_times", "money_control"],
                "config_schema": {
                    "include_nse": {"type": "boolean", "default": True},
                    "include_bse": {"type": "boolean", "default": False},
                    "include_futures": {"type": "boolean", "default": True},
                    "include_options": {"type": "boolean", "default": False}
                },
                "config_values": {
                    "include_nse": True,
                    "include_bse": False,
                    "include_futures": True,
                    "include_options": False
                }
            },
            {
                "feature_name": "ai_predictions",
                "display_name": "AI-Powered Predictions",
                "description": "Machine learning models for price predictions and trading signals",
                "category": "ai_ml",
                "priority": 8,
                "required_apis": ["openai", "anthropic"],
                "optional_apis": ["google_ai", "azure_ai"],
                "config_schema": {
                    "prediction_models": {"type": "array", "default": ["lstm", "random_forest", "xgboost"]},
                    "confidence_threshold": {"type": "float", "default": 0.7, "min": 0.5, "max": 0.95},
                    "enable_ensemble": {"type": "boolean", "default": True},
                    "retrain_frequency_hours": {"type": "integer", "default": 24, "min": 1, "max": 168}
                },
                "config_values": {
                    "prediction_models": ["lstm", "random_forest", "xgboost"],
                    "confidence_threshold": 0.7,
                    "enable_ensemble": True,
                    "retrain_frequency_hours": 24
                }
            },
            {
                "feature_name": "news_sentiment",
                "display_name": "News & Sentiment Analysis",
                "description": "Real-time news feeds and sentiment analysis for market insights",
                "category": "news_sentiment", 
                "priority": 7,
                "required_apis": ["news_api"],
                "optional_apis": ["twitter_api", "reddit_api", "economic_times"],
                "config_schema": {
                    "news_sources": {"type": "array", "default": ["reuters", "bloomberg", "economic_times"]},
                    "sentiment_analysis": {"type": "boolean", "default": True},
                    "language_filter": {"type": "array", "default": ["en", "hi"]},
                    "update_frequency_minutes": {"type": "integer", "default": 15, "min": 5, "max": 60}
                },
                "config_values": {
                    "news_sources": ["reuters", "bloomberg", "economic_times"],
                    "sentiment_analysis": True,
                    "language_filter": ["en", "hi"],
                    "update_frequency_minutes": 15
                }
            },
            {
                "feature_name": "interactive_charts",
                "display_name": "Interactive Charts",
                "description": "Advanced charting with technical indicators and drawing tools",
                "category": "market_data",
                "priority": 8,
                "required_apis": [],
                "optional_apis": ["tradingview"],
                "depends_on_features": ["live_market_data", "historical_data"],
                "config_schema": {
                    "chart_types": {"type": "array", "default": ["candlestick", "line", "area", "ohlc"]},
                    "technical_indicators": {"type": "array", "default": ["sma", "ema", "rsi", "macd", "bollinger"]},
                    "enable_drawing_tools": {"type": "boolean", "default": True},
                    "max_chart_history_days": {"type": "integer", "default": 365, "min": 30, "max": 1095}
                },
                "config_values": {
                    "chart_types": ["candlestick", "line", "area", "ohlc"],
                    "technical_indicators": ["sma", "ema", "rsi", "macd", "bollinger"],
                    "enable_drawing_tools": True,
                    "max_chart_history_days": 365
                }
            },
            {
                "feature_name": "portfolio_tracking",
                "display_name": "Portfolio Tracking",
                "description": "Real-time portfolio monitoring and performance analytics",
                "category": "trading",
                "priority": 9,
                "required_apis": [],
                "optional_apis": [],
                "depends_on_features": ["live_market_data"],
                "config_schema": {
                    "real_time_updates": {"type": "boolean", "default": True},
                    "performance_metrics": {"type": "array", "default": ["pnl", "returns", "sharpe", "max_drawdown"]},
                    "benchmark_comparison": {"type": "boolean", "default": True},
                    "tax_calculation": {"type": "boolean", "default": True}
                },
                "config_values": {
                    "real_time_updates": True,
                    "performance_metrics": ["pnl", "returns", "sharpe", "max_drawdown"],
                    "benchmark_comparison": True,
                    "tax_calculation": True
                }
            },
            {
                "feature_name": "email_notifications",
                "display_name": "Email Notifications",
                "description": "Email alerts for trading signals, portfolio updates, and system events",
                "category": "communication",
                "priority": 6,
                "required_apis": ["sendgrid", "aws_ses"],
                "optional_apis": ["twilio"],
                "config_schema": {
                    "notification_types": {"type": "array", "default": ["trade_signals", "portfolio_alerts", "system_updates"]},
                    "email_frequency": {"type": "string", "default": "immediate", "options": ["immediate", "daily", "weekly"]},
                    "enable_html_emails": {"type": "boolean", "default": True}
                },
                "config_values": {
                    "notification_types": ["trade_signals", "portfolio_alerts", "system_updates"],
                    "email_frequency": "immediate",
                    "enable_html_emails": True
                }
            },
            {
                "feature_name": "sms_alerts",
                "display_name": "SMS Alerts",
                "description": "SMS notifications for urgent trading alerts and security events",
                "category": "communication",
                "priority": 5,
                "required_apis": ["twilio"],
                "optional_apis": [],
                "config_schema": {
                    "alert_types": {"type": "array", "default": ["urgent_signals", "security_alerts", "trade_execution"]},
                    "rate_limit_per_hour": {"type": "integer", "default": 10, "min": 1, "max": 50}
                },
                "config_values": {
                    "alert_types": ["urgent_signals", "security_alerts", "trade_execution"],
                    "rate_limit_per_hour": 10
                }
            },
            {
                "feature_name": "system_monitoring",
                "display_name": "System Monitoring",
                "description": "Real-time system health monitoring and performance tracking",
                "category": "infrastructure",
                "priority": 9,
                "required_apis": [],
                "optional_apis": ["datadog", "new_relic"],
                "config_schema": {
                    "health_check_interval_seconds": {"type": "integer", "default": 30, "min": 10, "max": 300},
                    "alert_thresholds": {
                        "type": "object",
                        "default": {
                            "cpu_usage": 80,
                            "memory_usage": 85,
                            "api_error_rate": 5,
                            "response_time_ms": 1000
                        }
                    },
                    "enable_auto_scaling": {"type": "boolean", "default": False}
                },
                "config_values": {
                    "health_check_interval_seconds": 30,
                    "alert_thresholds": {
                        "cpu_usage": 80,
                        "memory_usage": 85,
                        "api_error_rate": 5,
                        "response_time_ms": 1000
                    },
                    "enable_auto_scaling": False
                }
            }
        ]
        
        for feature_data in default_features:
            # Check if feature already exists
            existing_feature = db.query(SystemFeatureConfig).filter(
                SystemFeatureConfig.feature_name == feature_data["feature_name"]
            ).first()
            
            if not existing_feature:
                feature = SystemFeatureConfig(
                    feature_name=feature_data["feature_name"],
                    display_name=feature_data["display_name"],
                    description=feature_data["description"],
                    category=feature_data["category"],
                    priority=feature_data["priority"],
                    required_apis=feature_data["required_apis"],
                    optional_apis=feature_data.get("optional_apis", []),
                    depends_on_features=feature_data.get("depends_on_features", []),
                    config_schema=feature_data["config_schema"],
                    config_values=feature_data["config_values"],
                    is_enabled=False  # Start disabled until APIs are configured
                )
                
                db.add(feature)
                logger.info(f"Created default feature: {feature_data['feature_name']}")
        
        db.commit()
        logger.info("Default system features setup completed")
    
    @staticmethod
    def create_initial_admin(db: Session, email: str, username: str, password: str) -> Admin:
        """Create the initial super admin user"""
        
        # Check if super admin already exists
        existing_admin = db.query(Admin).filter(
            Admin.role == AdminRoleEnum.SUPER_ADMIN
        ).first()
        
        if existing_admin:
            logger.info("Super admin already exists")
            return existing_admin
        
        # Create super admin
        hashed_password = auth_service.hash_password(password)
        
        admin = Admin(
            username=username,
            email=email,
            password_hash=hashed_password,
            first_name="System",
            last_name="Administrator",
            role=AdminRoleEnum.SUPER_ADMIN,
            role_level=5,
            department="System",
            
            # Grant all permissions
            can_manage_users=True,
            can_manage_admins=True,
            can_manage_trading=True,
            can_manage_financials=True,
            can_manage_ml_models=True,
            can_manage_system=True,
            can_manage_content=True,
            can_manage_support=True,
            can_view_analytics=True,
            can_export_data=True,
            can_emergency_stop=True,
            
            # High approval limits
            refund_approval_limit=1000000.0,  # 10 lakh INR
            user_action_approval_limit=10000,
            
            # Security settings
            max_concurrent_sessions=5,
            session_timeout_minutes=480,  # 8 hours
            
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        logger.info(f"Created initial super admin: {username}")
        return admin
    
    @staticmethod
    def setup_system(db: Session, 
                    admin_email: str = "admin@tradingplatform.com",
                    admin_username: str = "superadmin", 
                    admin_password: str = "ChangeMe123!@#"):
        """Complete system setup"""
        
        logger.info("Starting system setup...")
        
        # Create default features
        SystemSetupService.create_default_features(db)
        
        # Create initial admin
        admin = SystemSetupService.create_initial_admin(db, admin_email, admin_username, admin_password)
        
        logger.info("System setup completed successfully")
        logger.warning(f"IMPORTANT: Change the default admin password for {admin_username}")
        
        return {
            "admin_created": True,
            "admin_username": admin_username,
            "admin_email": admin_email,
            "features_created": True,
            "setup_completed": True
        }


def run_initial_setup():
    """Run initial system setup - call this during application startup"""
    db = next(get_db())
    try:
        result = SystemSetupService.setup_system(db)
        logger.info("Initial system setup completed")
        return result
    except Exception as e:
        logger.error(f"System setup failed: {str(e)}")
        raise
    finally:
        db.close()