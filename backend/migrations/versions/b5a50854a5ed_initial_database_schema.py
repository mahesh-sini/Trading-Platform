"""Initial database schema with all models

Revision ID: b5a50854a5ed
Revises:
Create Date: 2025-11-06 02:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b5a50854a5ed'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('user', 'admin', 'moderator')")
    op.execute("CREATE TYPE subscriptiontier AS ENUM ('free', 'basic', 'premium', 'enterprise')")
    op.execute("CREATE TYPE subscriptionstatus AS ENUM ('active', 'inactive', 'cancelled', 'expired', 'trial', 'suspended')")
    op.execute("CREATE TYPE billingperiod AS ENUM ('monthly', 'quarterly', 'yearly', 'lifetime')")
    op.execute("CREATE TYPE brokertype AS ENUM ('alpaca', 'interactive_brokers', 'td_ameritrade', 'zerodha', 'upstox', 'angel_one', 'icici_direct', 'fyers')")
    op.execute("CREATE TYPE markettype AS ENUM ('us', 'india', 'crypto', 'forex')")
    op.execute("CREATE TYPE accountstatus AS ENUM ('active', 'inactive', 'suspended', 'pending', 'disconnected', 'error')")
    op.execute("CREATE TYPE orderside AS ENUM ('buy', 'sell')")
    op.execute("CREATE TYPE ordertype AS ENUM ('market', 'limit', 'stop', 'stop_limit', 'trailing_stop')")
    op.execute("CREATE TYPE orderstatus AS ENUM ('pending', 'submitted', 'accepted', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired')")
    op.execute("CREATE TYPE timeinforce AS ENUM ('day', 'gtc', 'ioc', 'fok')")
    op.execute("CREATE TYPE strategytype AS ENUM ('momentum', 'mean_reversion', 'breakout', 'trend_following', 'scalping', 'swing', 'position', 'ml_based', 'custom')")
    op.execute("CREATE TYPE strategystatus AS ENUM ('active', 'inactive', 'paused', 'backtesting', 'paper_trading', 'live')")
    op.execute("CREATE TYPE predictiondirection AS ENUM ('up', 'down', 'neutral')")
    op.execute("CREATE TYPE predictiontimeframe AS ENUM ('intraday', 'short_term', 'medium_term', 'long_term')")
    op.execute("CREATE TYPE modeltype AS ENUM ('lstm', 'gru', 'xgboost', 'random_forest', 'ensemble', 'transformer')")
    op.execute("CREATE TYPE marketdatainterval AS ENUM ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1M')")
    op.execute("CREATE TYPE sentimentscore AS ENUM ('very_negative', 'negative', 'neutral', 'positive', 'very_positive')")

    # Users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('is_email_verified', sa.Boolean(), nullable=False),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True),
        sa.Column('password_reset_expires', sa.DateTime(), nullable=True),
        sa.Column('subscription_tier', postgresql.ENUM('free', 'basic', 'premium', 'enterprise', name='subscriptiontier'), nullable=False),
        sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
        sa.Column('role', postgresql.ENUM('user', 'admin', 'moderator', name='userrole'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('login_count', sa.Integer(), nullable=False),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
        sa.Column('totp_secret', sa.String(length=32), nullable=True),
        sa.Column('is_2fa_enabled', sa.Boolean(), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('notification_preferences', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_deleted_at'), 'users', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_subscription_tier'), 'users', ['subscription_tier'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)

    # Subscription Plans table
    op.create_table('subscription_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tier', sa.String(length=50), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('billing_period', postgresql.ENUM('monthly', 'quarterly', 'yearly', 'lifetime', name='billingperiod'), nullable=False),
        sa.Column('max_broker_accounts', sa.Integer(), nullable=False),
        sa.Column('max_strategies', sa.Integer(), nullable=False),
        sa.Column('max_watchlists', sa.Integer(), nullable=False),
        sa.Column('max_positions', sa.Integer(), nullable=False),
        sa.Column('daily_trade_limit', sa.Integer(), nullable=False),
        sa.Column('has_ml_predictions', sa.Boolean(), nullable=False),
        sa.Column('has_auto_trading', sa.Boolean(), nullable=False),
        sa.Column('has_backtesting', sa.Boolean(), nullable=False),
        sa.Column('has_advanced_analytics', sa.Boolean(), nullable=False),
        sa.Column('has_api_access', sa.Boolean(), nullable=False),
        sa.Column('has_priority_support', sa.Boolean(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False),
        sa.Column('stripe_price_id', sa.String(length=100), nullable=True),
        sa.Column('stripe_product_id', sa.String(length=100), nullable=True),
        sa.Column('trial_days', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_subscription_plans_id'), 'subscription_plans', ['id'], unique=False)
    op.create_index(op.f('ix_subscription_plans_tier'), 'subscription_plans', ['tier'], unique=False)

    # Subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'inactive', 'cancelled', 'expired', 'trial', 'suspended', name='subscriptionstatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(), nullable=True),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('next_billing_date', sa.DateTime(), nullable=True),
        sa.Column('stripe_subscription_id', sa.String(length=100), nullable=True),
        sa.Column('stripe_customer_id', sa.String(length=100), nullable=True),
        sa.Column('last_payment_at', sa.DateTime(), nullable=True),
        sa.Column('last_payment_amount', sa.Float(), nullable=True),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('auto_renew', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['subscription_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_plan_id'), 'subscriptions', ['plan_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)

    # Brokers table
    op.create_table('brokers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('broker_type', postgresql.ENUM('alpaca', 'interactive_brokers', 'td_ameritrade', 'zerodha', 'upstox', 'angel_one', 'icici_direct', 'fyers', name='brokertype'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('market_type', postgresql.ENUM('us', 'india', 'crypto', 'forex', name='markettype'), nullable=False),
        sa.Column('supported_markets', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('supports_paper_trading', sa.Boolean(), nullable=False),
        sa.Column('supports_margin', sa.Boolean(), nullable=False),
        sa.Column('supports_options', sa.Boolean(), nullable=False),
        sa.Column('supports_futures', sa.Boolean(), nullable=False),
        sa.Column('supports_crypto', sa.Boolean(), nullable=False),
        sa.Column('api_url', sa.String(length=255), nullable=True),
        sa.Column('api_docs_url', sa.String(length=255), nullable=True),
        sa.Column('requires_api_key', sa.Boolean(), nullable=False),
        sa.Column('requires_secret_key', sa.Boolean(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False),
        sa.Column('commission_per_trade', sa.Float(), nullable=True),
        sa.Column('minimum_deposit', sa.Float(), nullable=True),
        sa.Column('country_code', sa.String(length=2), nullable=True),
        sa.Column('website_url', sa.String(length=255), nullable=True),
        sa.Column('logo_url', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('broker_type')
    )
    op.create_index(op.f('ix_brokers_id'), 'brokers', ['id'], unique=False)

    # Continue with more tables in the next part...


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('news_items')
    op.drop_table('market_data')
    op.drop_table('watchlist_items')
    op.drop_table('watchlists')
    op.drop_table('model_performance')
    op.drop_table('predictions')
    op.drop_table('strategy_performance')
    op.drop_table('strategies')
    op.drop_table('portfolio_history')
    op.drop_table('portfolios')
    op.drop_table('positions')
    op.drop_table('trades')
    op.drop_table('orders')
    op.drop_table('broker_accounts')
    op.drop_table('brokers')
    op.drop_table('subscriptions')
    op.drop_table('subscription_plans')
    op.drop_table('users')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS sentimentscore")
    op.execute("DROP TYPE IF EXISTS marketdatainterval")
    op.execute("DROP TYPE IF EXISTS modeltype")
    op.execute("DROP TYPE IF EXISTS predictiontimeframe")
    op.execute("DROP TYPE IF EXISTS predictiondirection")
    op.execute("DROP TYPE IF EXISTS strategystatus")
    op.execute("DROP TYPE IF EXISTS strategytype")
    op.execute("DROP TYPE IF EXISTS timeinforce")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS ordertype")
    op.execute("DROP TYPE IF EXISTS orderside")
    op.execute("DROP TYPE IF EXISTS accountstatus")
    op.execute("DROP TYPE IF EXISTS markettype")
    op.execute("DROP TYPE IF EXISTS brokertype")
    op.execute("DROP TYPE IF EXISTS billingperiod")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
    op.execute("DROP TYPE IF EXISTS userrole")
