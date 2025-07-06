-- Initialize Trading Platform Database
-- This script is executed when PostgreSQL container starts

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create database if not exists
SELECT 'CREATE DATABASE trading_platform'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'trading_platform')\gexec

-- Connect to the database
\c trading_platform;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Set search path
SET search_path TO public, trading, analytics;

-- Create custom types
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscription_tier') THEN
        CREATE TYPE subscription_tier AS ENUM ('free', 'basic', 'pro', 'enterprise');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_side') THEN
        CREATE TYPE order_side AS ENUM ('buy', 'sell');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_type') THEN
        CREATE TYPE order_type AS ENUM ('market', 'limit', 'stop', 'stop_limit');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'order_status') THEN
        CREATE TYPE order_status AS ENUM ('pending', 'filled', 'partially_filled', 'cancelled', 'rejected');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'prediction_type') THEN
        CREATE TYPE prediction_type AS ENUM ('price', 'trend', 'volatility');
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'strategy_type') THEN
        CREATE TYPE strategy_type AS ENUM ('mean_reversion', 'momentum', 'arbitrage', 'ml_based');
    END IF;
END $$;

-- Create indexes for performance
-- These will be created by Alembic migrations, but we can add some basic ones

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE trading_platform TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO postgres;

-- Create a read-only user for analytics
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analytics_user') THEN
        CREATE ROLE analytics_user WITH LOGIN PASSWORD 'analytics123';
        GRANT CONNECT ON DATABASE trading_platform TO analytics_user;
        GRANT USAGE ON SCHEMA public TO analytics_user;
        GRANT USAGE ON SCHEMA trading TO analytics_user;
        GRANT USAGE ON SCHEMA analytics TO analytics_user;
        GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
        GRANT SELECT ON ALL TABLES IN SCHEMA trading TO analytics_user;
        GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO analytics_user;
    END IF;
END $$;

-- Insert default data
-- This will be handled by the application, but we can add some reference data

COMMIT;