from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
import enum


class SubscriptionStatus(str, enum.Enum):
    """Subscription status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TRIAL = "trial"
    SUSPENDED = "suspended"


class BillingPeriod(str, enum.Enum):
    """Billing period enumeration"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class SubscriptionPlan(BaseModel):
    """Subscription plan model"""
    __tablename__ = "subscription_plans"

    # Plan details
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    tier = Column(String(50), nullable=False, index=True)  # free, basic, premium, enterprise

    # Pricing
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    billing_period = Column(SQLEnum(BillingPeriod), nullable=False)

    # Features and limits
    max_broker_accounts = Column(Integer, default=1, nullable=False)
    max_strategies = Column(Integer, default=3, nullable=False)
    max_watchlists = Column(Integer, default=5, nullable=False)
    max_positions = Column(Integer, default=10, nullable=False)
    daily_trade_limit = Column(Integer, default=10, nullable=False)

    # Feature flags
    has_ml_predictions = Column(Boolean, default=False, nullable=False)
    has_auto_trading = Column(Boolean, default=False, nullable=False)
    has_backtesting = Column(Boolean, default=False, nullable=False)
    has_advanced_analytics = Column(Boolean, default=False, nullable=False)
    has_api_access = Column(Boolean, default=False, nullable=False)
    has_priority_support = Column(Boolean, default=False, nullable=False)

    # Availability
    is_available = Column(Boolean, default=True, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)

    # Stripe integration
    stripe_price_id = Column(String(100), nullable=True)
    stripe_product_id = Column(String(100), nullable=True)

    # Trial
    trial_days = Column(Integer, default=0, nullable=False)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")

    def __repr__(self):
        return f"<SubscriptionPlan(name={self.name}, price={self.price}, period={self.billing_period})>"


class Subscription(BaseModel):
    """User subscription model"""
    __tablename__ = "subscriptions"

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Plan reference
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False, index=True)

    # Status
    status = Column(
        SQLEnum(SubscriptionStatus),
        default=SubscriptionStatus.INACTIVE,
        nullable=False,
        index=True
    )

    # Dates
    started_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)

    # Billing
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    next_billing_date = Column(DateTime, nullable=True)

    # Payment
    stripe_subscription_id = Column(String(100), nullable=True, unique=True)
    stripe_customer_id = Column(String(100), nullable=True)
    last_payment_at = Column(DateTime, nullable=True)
    last_payment_amount = Column(Float, nullable=True)

    # Cancellation
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    cancellation_reason = Column(Text, nullable=True)

    # Auto-renewal
    auto_renew = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, plan={self.plan_id}, status={self.status})>"

    @property
    def is_active(self):
        """Check if subscription is active"""
        from datetime import datetime
        return (
            self.status == SubscriptionStatus.ACTIVE and
            (self.expires_at is None or self.expires_at > datetime.utcnow())
        )

    @property
    def is_trial(self):
        """Check if subscription is in trial period"""
        from datetime import datetime
        return (
            self.status == SubscriptionStatus.TRIAL and
            self.trial_ends_at and
            self.trial_ends_at > datetime.utcnow()
        )

    @property
    def days_until_expiry(self):
        """Get days until subscription expires"""
        if not self.expires_at:
            return None
        from datetime import datetime
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
