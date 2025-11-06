from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, Float, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
import enum


class BrokerType(str, enum.Enum):
    """Broker type enumeration"""
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    ZERODHA = "zerodha"
    UPSTOX = "upstox"
    ANGEL_ONE = "angel_one"
    ICICI_DIRECT = "icici_direct"
    FYERS = "fyers"


class MarketType(str, enum.Enum):
    """Market type enumeration"""
    US = "us"
    INDIA = "india"
    CRYPTO = "crypto"
    FOREX = "forex"


class AccountStatus(str, enum.Enum):
    """Account status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class Broker(BaseModel):
    """Broker definition model"""
    __tablename__ = "brokers"

    # Broker details
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    broker_type = Column(SQLEnum(BrokerType), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    # Market support
    market_type = Column(SQLEnum(MarketType), nullable=False)
    supported_markets = Column(JSON, nullable=True)  # List of supported exchanges

    # Features
    supports_paper_trading = Column(Boolean, default=False, nullable=False)
    supports_margin = Column(Boolean, default=False, nullable=False)
    supports_options = Column(Boolean, default=False, nullable=False)
    supports_futures = Column(Boolean, default=False, nullable=False)
    supports_crypto = Column(Boolean, default=False, nullable=False)

    # API details
    api_url = Column(String(255), nullable=True)
    api_docs_url = Column(String(255), nullable=True)
    requires_api_key = Column(Boolean, default=True, nullable=False)
    requires_secret_key = Column(Boolean, default=False, nullable=False)

    # Availability
    is_available = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)

    # Fees and limits
    commission_per_trade = Column(Float, nullable=True)
    minimum_deposit = Column(Float, nullable=True)

    # Country/region
    country_code = Column(String(2), nullable=True)  # ISO 2-letter country code
    website_url = Column(String(255), nullable=True)
    logo_url = Column(String(255), nullable=True)

    # Relationships
    broker_accounts = relationship("BrokerAccount", back_populates="broker")

    def __repr__(self):
        return f"<Broker(name={self.name}, type={self.broker_type})>"


class BrokerAccount(BaseModel):
    """User broker account connection model"""
    __tablename__ = "broker_accounts"

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Broker reference
    broker_id = Column(UUID(as_uuid=True), ForeignKey("brokers.id"), nullable=False, index=True)

    # Account details
    account_name = Column(String(100), nullable=False)
    account_number = Column(String(100), nullable=True)
    account_type = Column(String(50), nullable=True)  # cash, margin, retirement, etc.

    # Status
    status = Column(
        SQLEnum(AccountStatus),
        default=AccountStatus.PENDING,
        nullable=False,
        index=True
    )

    # API credentials (encrypted)
    api_key = Column(String(500), nullable=True)
    api_secret = Column(String(500), nullable=True)
    access_token = Column(String(500), nullable=True)
    refresh_token = Column(String(500), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)

    # Account settings
    is_paper_trading = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Connection tracking
    last_connected_at = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    connection_error = Column(Text, nullable=True)

    # Account balance (cached)
    buying_power = Column(Float, default=0.0, nullable=False)
    cash_balance = Column(Float, default=0.0, nullable=False)
    portfolio_value = Column(Float, default=0.0, nullable=False)
    last_balance_update = Column(DateTime, nullable=True)

    # Metadata
    account_metadata = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="broker_accounts")
    broker = relationship("Broker", back_populates="broker_accounts")
    trades = relationship("Trade", back_populates="broker_account")
    orders = relationship("Order", back_populates="broker_account")
    positions = relationship("Position", back_populates="broker_account")

    def __repr__(self):
        return f"<BrokerAccount(user_id={self.user_id}, broker={self.broker_id}, status={self.status})>"

    @property
    def is_connected(self):
        """Check if account is currently connected"""
        return self.status == AccountStatus.ACTIVE

    @property
    def needs_reconnection(self):
        """Check if account needs reconnection"""
        from datetime import datetime, timedelta
        if not self.last_connected_at:
            return True
        return datetime.utcnow() - self.last_connected_at > timedelta(hours=24)

    @property
    def display_account_number(self):
        """Get masked account number for display"""
        if not self.account_number:
            return "N/A"
        if len(self.account_number) <= 4:
            return self.account_number
        return f"****{self.account_number[-4:]}"
