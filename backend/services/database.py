from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from typing import AsyncGenerator
import logging

logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL for sync operations"""
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/trading_platform")
    
    # For local testing without Docker, use SQLite if PostgreSQL is not available
    if "localhost" in db_url and not os.getenv("FORCE_POSTGRES"):
        return "sqlite:///./trading_platform.db"
    
    return db_url

# Database configuration
DATABASE_URL = get_database_url()

# For local testing without Docker, use SQLite if PostgreSQL is not available
if "localhost" in DATABASE_URL and not os.getenv("FORCE_POSTGRES"):
    DATABASE_URL = "sqlite:///./trading_platform.db"
    ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./trading_platform.db"
else:
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=os.getenv("ENVIRONMENT") == "development",
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Sync engine for migrations
sync_engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("ENVIRONMENT") == "development",
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Sync session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

def get_sync_db():
    """Get synchronous database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Sync database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

async def init_db():
    """Initialize database connection"""
    try:
        async with engine.begin() as conn:
            # Import all models to register them
            from models.base import Base
            from models import (
                User, Subscription, SubscriptionPlan, BrokerAccount,
                Trade, Order, Position, Prediction, ModelPerformance,
                Portfolio, PortfolioHistory, Strategy, StrategyPerformance,
                Watchlist, WatchlistItem, MarketData, NewsItem
            )
            
            # Create tables if they don't exist
            # await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

async def close_db():
    """Close database connection"""
    try:
        await engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {str(e)}")

# Database health check
async def check_db_health() -> bool:
    """Check if database is healthy"""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return False