"""
Database models for the AI Trading Platform.

This module exports all database models for easy importing throughout the application.
"""

from models.base import Base, BaseModel

# User and authentication models
from models.user import User, UserRole, SubscriptionTier

# Subscription models
from models.subscription import (
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingPeriod
)

# Broker models
from models.broker import (
    Broker,
    BrokerAccount,
    BrokerType,
    MarketType,
    AccountStatus
)

# Trading models
from models.trade import (
    Order,
    Trade,
    Position,
    OrderSide,
    OrderType,
    OrderStatus,
    TimeInForce
)

# Portfolio models
from models.portfolio import (
    Portfolio,
    PortfolioHistory
)

# Strategy models
from models.strategy import (
    Strategy,
    StrategyPerformance,
    StrategyType,
    StrategyStatus
)

# Prediction and ML models
from models.prediction import (
    Prediction,
    ModelPerformance,
    PredictionDirection,
    PredictionTimeframe,
    ModelType
)

# Watchlist models
from models.watchlist import (
    Watchlist,
    WatchlistItem
)

# Market data models
from models.market_data import (
    MarketData,
    NewsItem,
    MarketDataInterval,
    SentimentScore
)

__all__ = [
    # Base
    "Base",
    "BaseModel",

    # User models
    "User",
    "UserRole",
    "SubscriptionTier",

    # Subscription models
    "Subscription",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "BillingPeriod",

    # Broker models
    "Broker",
    "BrokerAccount",
    "BrokerType",
    "MarketType",
    "AccountStatus",

    # Trading models
    "Order",
    "Trade",
    "Position",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "TimeInForce",

    # Portfolio models
    "Portfolio",
    "PortfolioHistory",

    # Strategy models
    "Strategy",
    "StrategyPerformance",
    "StrategyType",
    "StrategyStatus",

    # Prediction models
    "Prediction",
    "ModelPerformance",
    "PredictionDirection",
    "PredictionTimeframe",
    "ModelType",

    # Watchlist models
    "Watchlist",
    "WatchlistItem",

    # Market data models
    "MarketData",
    "NewsItem",
    "MarketDataInterval",
    "SentimentScore",
]
