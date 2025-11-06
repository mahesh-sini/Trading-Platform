from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
from datetime import datetime


class Portfolio(BaseModel):
    """Portfolio model for tracking overall portfolio"""
    __tablename__ = "portfolios"

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    # Portfolio name
    name = Column(String(100), default="My Portfolio", nullable=False)

    # Current values
    total_value = Column(Float, default=0.0, nullable=False)
    cash_balance = Column(Float, default=0.0, nullable=False)
    invested_value = Column(Float, default=0.0, nullable=False)
    buying_power = Column(Float, default=0.0, nullable=False)

    # Performance metrics
    total_pnl = Column(Float, default=0.0, nullable=False)
    total_pnl_percent = Column(Float, default=0.0, nullable=False)
    day_pnl = Column(Float, default=0.0, nullable=False)
    day_pnl_percent = Column(Float, default=0.0, nullable=False)

    # Historical performance
    initial_value = Column(Float, default=0.0, nullable=False)
    all_time_high = Column(Float, default=0.0, nullable=False)
    all_time_high_date = Column(DateTime, nullable=True)
    all_time_low = Column(Float, nullable=True)
    all_time_low_date = Column(DateTime, nullable=True)

    # Drawdown tracking
    max_drawdown = Column(Float, default=0.0, nullable=False)
    max_drawdown_percent = Column(Float, default=0.0, nullable=False)
    current_drawdown_percent = Column(Float, default=0.0, nullable=False)

    # Risk metrics
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)

    # Trade statistics
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)
    avg_win = Column(Float, default=0.0, nullable=False)
    avg_loss = Column(Float, default=0.0, nullable=False)
    profit_factor = Column(Float, nullable=True)

    # Holdings summary
    total_positions = Column(Integer, default=0, nullable=False)
    long_positions = Column(Integer, default=0, nullable=False)
    short_positions = Column(Integer, default=0, nullable=False)

    # Asset allocation (JSON for flexibility)
    asset_allocation = Column(JSON, nullable=True)
    sector_allocation = Column(JSON, nullable=True)

    # Last update
    last_calculated_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="portfolios")
    history = relationship("PortfolioHistory", back_populates="portfolio", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Portfolio(user_id={self.user_id}, value={self.total_value}, pnl={self.total_pnl})>"

    @property
    def return_on_investment(self):
        """Calculate ROI percentage"""
        if self.initial_value == 0:
            return 0.0
        return ((self.total_value - self.initial_value) / self.initial_value) * 100

    @property
    def average_trade_size(self):
        """Calculate average trade size"""
        if self.total_trades == 0:
            return 0.0
        return self.invested_value / self.total_trades

    def update_metrics(self):
        """Update portfolio metrics"""
        # Win rate
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100

        # Profit factor
        if self.losing_trades > 0 and self.avg_loss != 0:
            total_wins = self.winning_trades * self.avg_win
            total_losses = abs(self.losing_trades * self.avg_loss)
            if total_losses != 0:
                self.profit_factor = total_wins / total_losses

        # Update all-time high/low
        if self.total_value > self.all_time_high:
            self.all_time_high = self.total_value
            self.all_time_high_date = datetime.utcnow()

        if self.all_time_low is None or self.total_value < self.all_time_low:
            self.all_time_low = self.total_value
            self.all_time_low_date = datetime.utcnow()

        # Update drawdown
        if self.all_time_high > 0:
            current_drawdown = self.all_time_high - self.total_value
            self.current_drawdown_percent = (current_drawdown / self.all_time_high) * 100

            if self.current_drawdown_percent > self.max_drawdown_percent:
                self.max_drawdown = current_drawdown
                self.max_drawdown_percent = self.current_drawdown_percent

        self.last_calculated_at = datetime.utcnow()


class PortfolioHistory(BaseModel):
    """Portfolio history model for tracking portfolio over time"""
    __tablename__ = "portfolio_history"

    # Portfolio reference
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True)

    # Snapshot date
    snapshot_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Values at snapshot time
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    invested_value = Column(Float, nullable=False)
    buying_power = Column(Float, nullable=False)

    # P&L at snapshot
    total_pnl = Column(Float, nullable=False)
    total_pnl_percent = Column(Float, nullable=False)
    day_pnl = Column(Float, nullable=False)
    day_pnl_percent = Column(Float, nullable=False)

    # Performance metrics
    sharpe_ratio = Column(Float, nullable=True)
    volatility = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)

    # Holdings at snapshot
    total_positions = Column(Integer, default=0, nullable=False)
    long_positions = Column(Integer, default=0, nullable=False)
    short_positions = Column(Integer, default=0, nullable=False)

    # Asset allocation snapshot
    asset_allocation = Column(JSON, nullable=True)
    sector_allocation = Column(JSON, nullable=True)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="history")

    def __repr__(self):
        return f"<PortfolioHistory(portfolio_id={self.portfolio_id}, date={self.snapshot_date}, value={self.total_value})>"
