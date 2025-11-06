from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
import enum
from datetime import datetime


class StrategyType(str, enum.Enum):
    """Strategy type enumeration"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"
    SCALPING = "scalping"
    SWING = "swing"
    POSITION = "position"
    ML_BASED = "ml_based"
    CUSTOM = "custom"


class StrategyStatus(str, enum.Enum):
    """Strategy status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE = "live"


class Strategy(BaseModel):
    """Trading strategy model"""
    __tablename__ = "strategies"

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Strategy details
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(SQLEnum(StrategyType), nullable=False, index=True)

    # Status
    status = Column(
        SQLEnum(StrategyStatus),
        default=StrategyStatus.INACTIVE,
        nullable=False,
        index=True
    )

    # Configuration (JSON for flexibility)
    config = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)

    # Trading rules
    symbols = Column(JSON, nullable=True)  # List of symbols to trade
    entry_conditions = Column(JSON, nullable=True)
    exit_conditions = Column(JSON, nullable=True)

    # Risk management
    max_position_size = Column(Float, nullable=True)
    max_positions = Column(Integer, default=5, nullable=False)
    stop_loss_percent = Column(Float, nullable=True)
    take_profit_percent = Column(Float, nullable=True)
    max_daily_loss = Column(Float, nullable=True)
    max_drawdown_percent = Column(Float, nullable=True)

    # Capital allocation
    allocated_capital = Column(Float, default=0.0, nullable=False)
    position_size_percent = Column(Float, default=10.0, nullable=False)

    # Performance tracking
    total_trades = Column(Integer, default=0, nullable=False)
    winning_trades = Column(Integer, default=0, nullable=False)
    losing_trades = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)

    # P&L
    total_pnl = Column(Float, default=0.0, nullable=False)
    total_pnl_percent = Column(Float, default=0.0, nullable=False)
    avg_win = Column(Float, default=0.0, nullable=False)
    avg_loss = Column(Float, default=0.0, nullable=False)
    profit_factor = Column(Float, nullable=True)

    # Risk metrics
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, default=0.0, nullable=False)
    current_drawdown = Column(Float, default=0.0, nullable=False)

    # ML model reference (if ML-based strategy)
    ml_model_id = Column(String(100), nullable=True)
    ml_model_version = Column(String(50), nullable=True)

    # Activity tracking
    last_trade_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)

    # Public/private
    is_public = Column(Boolean, default=False, nullable=False)
    is_template = Column(Boolean, default=False, nullable=False)

    # Backtesting results
    backtest_results = Column(JSON, nullable=True)
    backtest_completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="strategies")
    orders = relationship("Order", back_populates="strategy")
    trades = relationship("Trade", back_populates="strategy")
    performance_history = relationship("StrategyPerformance", back_populates="strategy", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, status={self.status}, pnl={self.total_pnl})>"

    @property
    def is_running(self):
        """Check if strategy is currently running"""
        return self.status in [StrategyStatus.ACTIVE, StrategyStatus.LIVE, StrategyStatus.PAPER_TRADING]

    @property
    def current_positions_count(self):
        """Get count of current open positions for this strategy"""
        # This would typically be calculated from the positions table
        return 0  # Placeholder

    def update_performance(self):
        """Update strategy performance metrics"""
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100

        if self.losing_trades > 0 and self.avg_loss != 0:
            total_wins = self.winning_trades * self.avg_win
            total_losses = abs(self.losing_trades * self.avg_loss)
            if total_losses != 0:
                self.profit_factor = total_wins / total_losses

        if self.allocated_capital > 0:
            self.total_pnl_percent = (self.total_pnl / self.allocated_capital) * 100


class StrategyPerformance(BaseModel):
    """Strategy performance history model"""
    __tablename__ = "strategy_performance"

    # Strategy reference
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)

    # Snapshot date
    snapshot_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Performance at snapshot
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=False)
    losing_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)

    # P&L at snapshot
    total_pnl = Column(Float, nullable=False)
    total_pnl_percent = Column(Float, nullable=False)
    day_pnl = Column(Float, nullable=False)
    avg_win = Column(Float, nullable=False)
    avg_loss = Column(Float, nullable=False)
    profit_factor = Column(Float, nullable=True)

    # Risk metrics at snapshot
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=False)
    current_drawdown = Column(Float, nullable=False)

    # Capital allocation
    allocated_capital = Column(Float, nullable=False)

    # Open positions
    open_positions = Column(Integer, default=0, nullable=False)

    # Relationships
    strategy = relationship("Strategy", back_populates="performance_history")

    def __repr__(self):
        return f"<StrategyPerformance(strategy_id={self.strategy_id}, date={self.snapshot_date}, pnl={self.total_pnl})>"
