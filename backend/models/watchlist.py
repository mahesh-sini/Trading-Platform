from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
from datetime import datetime


class Watchlist(BaseModel):
    """Watchlist model for organizing symbols"""
    __tablename__ = "watchlists"

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Watchlist details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Settings
    is_default = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    # Sorting and display
    sort_order = Column(Integer, default=0, nullable=False)
    color = Column(String(20), nullable=True)  # For UI customization

    # Statistics (cached)
    items_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User", back_populates="watchlists")
    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Watchlist(id={self.id}, name={self.name}, items={self.items_count})>"

    def update_items_count(self):
        """Update the count of items in watchlist"""
        self.items_count = len(self.items)


class WatchlistItem(BaseModel):
    """Watchlist item model for symbols in watchlists"""
    __tablename__ = "watchlist_items"

    # Watchlist reference
    watchlist_id = Column(UUID(as_uuid=True), ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True)

    # Symbol information
    symbol = Column(String(20), nullable=False, index=True)
    company_name = Column(String(200), nullable=True)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)

    # Current market data (cached)
    current_price = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    change_amount = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=True)

    # Day range
    day_high = Column(Float, nullable=True)
    day_low = Column(Float, nullable=True)

    # User notes and alerts
    notes = Column(Text, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    alert_price_above = Column(Float, nullable=True)
    alert_price_below = Column(Float, nullable=True)

    # Alerts status
    alert_enabled = Column(Boolean, default=False, nullable=False)
    alert_triggered = Column(Boolean, default=False, nullable=False)
    alert_triggered_at = Column(DateTime, nullable=True)

    # Display order
    sort_order = Column(Integer, default=0, nullable=False)

    # Added timestamp
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    watchlist = relationship("Watchlist", back_populates="items")

    # Unique constraint: one symbol per watchlist
    __table_args__ = (
        UniqueConstraint('watchlist_id', 'symbol', name='unique_watchlist_symbol'),
    )

    def __repr__(self):
        return f"<WatchlistItem(symbol={self.symbol}, price={self.current_price})>"

    def update_price(self, price: float, change_percent: float = None, volume: int = None):
        """Update current price and related data"""
        self.current_price = price
        self.last_updated = datetime.utcnow()

        if change_percent is not None:
            self.change_percent = change_percent
            self.change_amount = price * (change_percent / 100)

        if volume is not None:
            self.volume = volume

        # Check price alerts
        if self.alert_enabled and not self.alert_triggered:
            if self.alert_price_above and price >= self.alert_price_above:
                self.trigger_alert()
            elif self.alert_price_below and price <= self.alert_price_below:
                self.trigger_alert()

    def trigger_alert(self):
        """Trigger price alert"""
        self.alert_triggered = True
        self.alert_triggered_at = datetime.utcnow()

    def reset_alert(self):
        """Reset triggered alert"""
        self.alert_triggered = False
        self.alert_triggered_at = None

    @property
    def is_price_above_target(self):
        """Check if current price is above target"""
        if not self.target_price or not self.current_price:
            return False
        return self.current_price >= self.target_price

    @property
    def is_price_below_stop_loss(self):
        """Check if current price is below stop loss"""
        if not self.stop_loss_price or not self.current_price:
            return False
        return self.current_price <= self.stop_loss_price

    @property
    def distance_to_target_percent(self):
        """Calculate distance to target price in percentage"""
        if not self.target_price or not self.current_price:
            return None
        return ((self.target_price - self.current_price) / self.current_price) * 100
