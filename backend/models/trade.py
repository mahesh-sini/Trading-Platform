from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SQLEnum, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
import enum
from datetime import datetime


class OrderSide(str, enum.Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(str, enum.Enum):
    """Order status enumeration"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TimeInForce(str, enum.Enum):
    """Time in force enumeration"""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


class Order(BaseModel):
    """Order model for tracking all orders"""
    __tablename__ = "orders"

    # User and broker references
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Strategy reference (optional - manual orders won't have this)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True)

    # Order details
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False, index=True)
    order_type = Column(SQLEnum(OrderType), nullable=False)
    time_in_force = Column(SQLEnum(TimeInForce), default=TimeInForce.DAY, nullable=False)

    # Pricing
    limit_price = Column(Float, nullable=True)
    stop_price = Column(Float, nullable=True)
    trailing_percent = Column(Float, nullable=True)

    # Status
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False, index=True)

    # Execution details
    filled_quantity = Column(Integer, default=0, nullable=False)
    filled_avg_price = Column(Float, nullable=True)
    filled_at = Column(DateTime, nullable=True)

    # Broker tracking
    broker_order_id = Column(String(100), nullable=True, unique=True, index=True)
    submitted_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Costs and fees
    commission = Column(Float, default=0.0, nullable=False)
    fees = Column(Float, default=0.0, nullable=False)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)

    # Auto-trading flag
    is_auto_trade = Column(Boolean, default=False, nullable=False, index=True)

    # Metadata
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="orders")
    broker_account = relationship("BrokerAccount", back_populates="orders")
    strategy = relationship("Strategy", back_populates="orders")
    trade = relationship("Trade", back_populates="order", uselist=False)

    def __repr__(self):
        return f"<Order(id={self.id}, symbol={self.symbol}, side={self.side}, status={self.status})>"

    @property
    def is_complete(self):
        """Check if order is complete"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]

    @property
    def remaining_quantity(self):
        """Get remaining unfilled quantity"""
        return self.quantity - self.filled_quantity

    @property
    def fill_percentage(self):
        """Get fill percentage"""
        if self.quantity == 0:
            return 0
        return (self.filled_quantity / self.quantity) * 100


class Trade(BaseModel):
    """Trade model for completed trades"""
    __tablename__ = "trades"

    # User and broker references
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Order reference
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)

    # Strategy reference
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True, index=True)

    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False, index=True)
    price = Column(Float, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Costs
    commission = Column(Float, default=0.0, nullable=False)
    fees = Column(Float, default=0.0, nullable=False)
    total_cost = Column(Float, nullable=False)

    # P&L tracking
    unrealized_pnl = Column(Float, default=0.0, nullable=False)
    realized_pnl = Column(Float, nullable=True)

    # Broker tracking
    broker_trade_id = Column(String(100), nullable=True, index=True)

    # Auto-trading flag
    is_auto_trade = Column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="trades")
    broker_account = relationship("BrokerAccount", back_populates="trades")
    order = relationship("Order", back_populates="trade")
    strategy = relationship("Strategy", back_populates="trades")

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol={self.symbol}, side={self.side}, quantity={self.quantity})>"

    @property
    def net_cost(self):
        """Get net cost including fees"""
        return self.total_cost + self.commission + self.fees


class Position(BaseModel):
    """Position model for current holdings"""
    __tablename__ = "positions"

    # User and broker references
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False, index=True)

    # Position details
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)  # long (buy) or short (sell)

    # Pricing
    avg_entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    last_price_update = Column(DateTime, nullable=True)

    # Value
    market_value = Column(Float, nullable=True)
    cost_basis = Column(Float, nullable=False)

    # P&L
    unrealized_pnl = Column(Float, default=0.0, nullable=False)
    unrealized_pnl_percent = Column(Float, default=0.0, nullable=False)
    day_pnl = Column(Float, default=0.0, nullable=False)
    day_pnl_percent = Column(Float, default=0.0, nullable=False)

    # Broker tracking
    broker_position_id = Column(String(100), nullable=True)

    # Strategy tracking
    opened_by_strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="positions")
    broker_account = relationship("BrokerAccount", back_populates="positions")
    strategy = relationship("Strategy", foreign_keys=[opened_by_strategy_id])

    # Unique constraint on user, broker_account, and symbol
    __table_args__ = (
        # Index for quick lookups
    )

    def __repr__(self):
        return f"<Position(symbol={self.symbol}, quantity={self.quantity}, pnl={self.unrealized_pnl})>"

    @property
    def is_long(self):
        """Check if position is long"""
        return self.side == OrderSide.BUY

    @property
    def is_short(self):
        """Check if position is short"""
        return self.side == OrderSide.SELL

    def update_market_price(self, current_price: float):
        """Update current price and recalculate P&L"""
        self.current_price = current_price
        self.last_price_update = datetime.utcnow()

        # Calculate market value
        self.market_value = abs(self.quantity) * current_price

        # Calculate unrealized P&L
        if self.side == OrderSide.BUY:
            # Long position
            self.unrealized_pnl = (current_price - self.avg_entry_price) * self.quantity
        else:
            # Short position
            self.unrealized_pnl = (self.avg_entry_price - current_price) * abs(self.quantity)

        # Calculate P&L percentage
        if self.cost_basis != 0:
            self.unrealized_pnl_percent = (self.unrealized_pnl / self.cost_basis) * 100
