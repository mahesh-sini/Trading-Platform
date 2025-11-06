from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Enum as SQLEnum, Index
from models.base import BaseModel
import enum
from datetime import datetime


class MarketDataInterval(str, enum.Enum):
    """Market data interval enumeration"""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"


class MarketData(BaseModel):
    """Historical market data model"""
    __tablename__ = "market_data"

    # Symbol and timeframe
    symbol = Column(String(20), nullable=False, index=True)
    interval = Column(SQLEnum(MarketDataInterval), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)

    # Additional metrics
    vwap = Column(Float, nullable=True)  # Volume Weighted Average Price
    trade_count = Column(Integer, nullable=True)

    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_symbol_interval_timestamp', 'symbol', 'interval', 'timestamp'),
    )

    def __repr__(self):
        return f"<MarketData(symbol={self.symbol}, timestamp={self.timestamp}, close={self.close})>"

    @property
    def price_range(self):
        """Get price range (high - low)"""
        return self.high - self.low

    @property
    def price_change(self):
        """Get price change (close - open)"""
        return self.close - self.open

    @property
    def price_change_percent(self):
        """Get price change percentage"""
        if self.open == 0:
            return 0.0
        return ((self.close - self.open) / self.open) * 100

    @property
    def is_green(self):
        """Check if candle is green (close > open)"""
        return self.close > self.open

    @property
    def is_red(self):
        """Check if candle is red (close < open)"""
        return self.close < self.open


class SentimentScore(str, enum.Enum):
    """Sentiment score enumeration"""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


class NewsItem(BaseModel):
    """News item model for financial news"""
    __tablename__ = "news_items"

    # News details
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    url = Column(String(1000), nullable=False, unique=True)

    # Source information
    source = Column(String(100), nullable=False, index=True)
    author = Column(String(200), nullable=True)

    # Related symbols
    symbols = Column(String(200), nullable=True)  # Comma-separated list

    # Timestamps
    published_at = Column(DateTime, nullable=False, index=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Sentiment analysis
    sentiment_score = Column(Float, nullable=True)  # -1 to 1 scale
    sentiment_label = Column(SQLEnum(SentimentScore), nullable=True, index=True)
    sentiment_confidence = Column(Float, nullable=True)

    # Relevance and importance
    relevance_score = Column(Float, nullable=True)  # 0 to 1 scale
    importance_score = Column(Float, nullable=True)  # 0 to 1 scale

    # Categories and tags
    category = Column(String(100), nullable=True, index=True)
    tags = Column(String(500), nullable=True)

    # Engagement metrics
    views_count = Column(Integer, default=0, nullable=False)
    clicks_count = Column(Integer, default=0, nullable=False)

    # Image
    image_url = Column(String(1000), nullable=True)

    def __repr__(self):
        return f"<NewsItem(title={self.title[:50]}, published={self.published_at})>"

    @property
    def symbol_list(self):
        """Get list of symbols from comma-separated string"""
        if not self.symbols:
            return []
        return [s.strip() for s in self.symbols.split(',')]

    @property
    def is_positive(self):
        """Check if sentiment is positive"""
        return self.sentiment_label in [SentimentScore.POSITIVE, SentimentScore.VERY_POSITIVE]

    @property
    def is_negative(self):
        """Check if sentiment is negative"""
        return self.sentiment_label in [SentimentScore.NEGATIVE, SentimentScore.VERY_NEGATIVE]

    @property
    def age_in_hours(self):
        """Get age of news item in hours"""
        delta = datetime.utcnow() - self.published_at
        return delta.total_seconds() / 3600

    def increment_views(self):
        """Increment view count"""
        self.views_count += 1

    def increment_clicks(self):
        """Increment click count"""
        self.clicks_count += 1
