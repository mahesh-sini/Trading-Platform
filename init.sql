-- Database initialization script for Trading Platform
-- This script sets up the initial database structure

-- Create database if not exists (PostgreSQL doesn't support IF NOT EXISTS for databases in this context)
-- The database is created by the Docker container initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone
SET timezone = 'UTC';

-- Create application user (optional, for additional security)
-- CREATE USER trading_app WITH PASSWORD 'secure_password';
-- GRANT CONNECT ON DATABASE trading_platform TO trading_app;

-- Note: The actual table creation will be handled by Alembic migrations
-- This script only sets up the database extensions and basic configuration

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Trading Platform database initialized successfully at %', NOW();
END $$;