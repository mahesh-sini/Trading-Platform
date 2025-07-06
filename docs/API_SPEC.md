# AI Trading Platform - API Specification

## API Overview

The AI Trading Platform provides RESTful APIs for all core functionality, with WebSocket connections for real-time data. All APIs use JSON for data exchange and JWT tokens for authentication.

**Base URL**: `https://api.tradingplatform.com/v1`
**WebSocket URL**: `wss://ws.tradingplatform.com/v1`

## Authentication

### JWT Token Authentication
```http
Authorization: Bearer <jwt_token>
```

### API Key Authentication (Enterprise)
```http
X-API-Key: <api_key>
X-API-Secret: <api_secret>
```

## Core Endpoints

### 1. Authentication & User Management

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

**Response (201)**:
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "access_token": "jwt-token",
  "refresh_token": "refresh-token",
  "expires_in": 3600
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

#### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh-token"
}
```

#### Get User Profile
```http
GET /users/profile
Authorization: Bearer <jwt_token>
```

**Response (200)**:
```json
{
  "user_id": "uuid-string",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "subscription_tier": "pro",
  "account_status": "active",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### 2. Subscription Management

#### Get Subscription Plans
```http
GET /subscriptions/plans
```

**Response (200)**:
```json
{
  "plans": [
    {
      "plan_id": "basic",
      "name": "Basic",
      "price": 29.00,
      "currency": "USD",
      "interval": "month",
      "features": [
        "Basic predictions",
        "Manual trading",
        "5 watchlists"
      ]
    },
    {
      "plan_id": "pro",
      "name": "Pro",
      "price": 99.00,
      "currency": "USD",
      "interval": "month",
      "features": [
        "Advanced predictions",
        "Automated trading",
        "Unlimited watchlists",
        "Backtesting"
      ]
    }
  ]
}
```

#### Subscribe to Plan
```http
POST /subscriptions/subscribe
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "plan_id": "pro",
  "payment_method_id": "pm_stripe_id"
}
```

### 3. Broker Integration

#### Add Broker Account
```http
POST /brokers/accounts
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "broker_name": "alpaca",
  "api_key": "broker_api_key",
  "api_secret": "broker_api_secret",
  "environment": "paper", // or "live"
  "is_primary": true
}
```

**Response (201)**:
```json
{
  "account_id": "uuid-string",
  "broker_name": "alpaca",
  "environment": "paper",
  "status": "connected",
  "balance": 100000.00,
  "buying_power": 100000.00,
  "is_primary": true
}
```

#### Get Broker Accounts
```http
GET /brokers/accounts
Authorization: Bearer <jwt_token>
```

#### Test Broker Connection
```http
POST /brokers/accounts/{account_id}/test
Authorization: Bearer <jwt_token>
```

### 4. Trading Operations

#### Place Order
```http
POST /trading/orders
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "symbol": "AAPL",
  "quantity": 100,
  "side": "buy", // or "sell"
  "order_type": "market", // or "limit", "stop", "stop_limit"
  "time_in_force": "day", // or "gtc", "ioc", "fok"
  "limit_price": 150.00, // required for limit orders
  "stop_price": 145.00, // required for stop orders
  "account_id": "broker_account_id"
}
```

**Response (201)**:
```json
{
  "order_id": "uuid-string",
  "symbol": "AAPL",
  "quantity": 100,
  "side": "buy",
  "order_type": "market",
  "status": "pending",
  "submitted_at": "2025-07-03T14:30:00Z",
  "estimated_cost": 15000.00
}
```

#### Get Orders
```http
GET /trading/orders?status=open&limit=50&offset=0
Authorization: Bearer <jwt_token>
```

#### Cancel Order
```http
DELETE /trading/orders/{order_id}
Authorization: Bearer <jwt_token>
```

#### Get Positions
```http
GET /trading/positions
Authorization: Bearer <jwt_token>
```

**Response (200)**:
```json
{
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 100,
      "avg_cost": 148.50,
      "market_value": 15000.00,
      "unrealized_pnl": 150.00,
      "unrealized_pnl_percent": 1.01,
      "account_id": "broker_account_id"
    }
  ]
}
```

### 5. AI Predictions

#### Get Predictions
```http
GET /predictions?symbol=AAPL&timeframe=intraday&limit=10
Authorization: Bearer <jwt_token>
```

**Response (200)**:
```json
{
  "predictions": [
    {
      "prediction_id": "uuid-string",
      "symbol": "AAPL",
      "timeframe": "intraday",
      "predicted_price": 152.75,
      "current_price": 150.00,
      "predicted_direction": "up",
      "confidence_score": 0.78,
      "prediction_horizon": "4h",
      "created_at": "2025-07-03T14:30:00Z",
      "model_version": "ensemble_v2.1",
      "features_used": [
        "technical_indicators",
        "sentiment_analysis",
        "volume_analysis"
      ]
    }
  ]
}
```

#### Request Prediction
```http
POST /predictions/generate
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "symbol": "AAPL",
  "timeframe": "swing", // "intraday", "swing", "long_term"
  "prediction_horizon": "7d"
}
```

#### Get Model Performance
```http
GET /predictions/performance?model=ensemble_v2.1&timeframe=intraday
Authorization: Bearer <jwt_token>
```

### 6. Market Data

#### Get Real-time Quote
```http
GET /market/quotes/{symbol}
Authorization: Bearer <jwt_token>
```

**Response (200)**:
```json
{
  "symbol": "AAPL",
  "price": 150.25,
  "bid": 150.20,
  "ask": 150.30,
  "volume": 25430000,
  "change": 1.25,
  "change_percent": 0.84,
  "timestamp": "2025-07-03T14:30:15Z"
}
```

#### Get Historical Data
```http
GET /market/history/{symbol}?period=1y&interval=1d
Authorization: Bearer <jwt_token>
```

#### Get Market News
```http
GET /market/news?symbols=AAPL,MSFT&limit=20
Authorization: Bearer <jwt_token>
```

**Response (200)**:
```json
{
  "news": [
    {
      "news_id": "uuid-string",
      "headline": "Apple Reports Strong Q2 Earnings",
      "summary": "Apple Inc. reported better than expected earnings...",
      "sentiment_score": 0.65,
      "sentiment_label": "positive",
      "symbols": ["AAPL"],
      "source": "Reuters",
      "published_at": "2025-07-03T13:00:00Z",
      "url": "https://reuters.com/article/..."
    }
  ]
}
```

### 7. Portfolio Management

#### Get Portfolio Summary
```http
GET /portfolio/summary
Authorization: Bearer <jwt_token>
```

**Response (200)**:
```json
{
  "total_value": 125000.00,
  "cash": 25000.00,
  "invested": 100000.00,
  "day_pnl": 1250.00,
  "day_pnl_percent": 1.01,
  "total_pnl": 5000.00,
  "total_pnl_percent": 4.17,
  "positions_count": 8,
  "diversity_score": 0.75
}
```

#### Get Portfolio Analytics
```http
GET /portfolio/analytics?period=1y
Authorization: Bearer <jwt_token>
```

**Response (200)**:
```json
{
  "performance_metrics": {
    "total_return": 0.125,
    "annualized_return": 0.11,
    "sharpe_ratio": 1.45,
    "max_drawdown": -0.08,
    "win_rate": 0.65,
    "profit_factor": 1.35,
    "beta": 0.95,
    "alpha": 0.02
  },
  "sector_allocation": [
    {
      "sector": "Technology",
      "percentage": 45.0,
      "value": 56250.00
    }
  ]
}
```

### 8. Automated Trading

#### Create Trading Strategy
```http
POST /strategies
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "name": "AI Momentum Strategy",
  "description": "Uses AI predictions with momentum indicators",
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "position_size": 0.1, // 10% of portfolio per position
  "risk_management": {
    "stop_loss_percent": 0.05,
    "take_profit_percent": 0.15,
    "max_drawdown_percent": 0.20
  },
  "entry_conditions": {
    "min_confidence_score": 0.70,
    "prediction_timeframe": "swing",
    "technical_indicators": ["RSI", "MACD"]
  },
  "is_active": true
}
```

#### Get Active Strategies
```http
GET /strategies?status=active
Authorization: Bearer <jwt_token>
```

#### Update Strategy
```http
PUT /strategies/{strategy_id}
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "is_active": false,
  "risk_management": {
    "stop_loss_percent": 0.03
  }
}
```

### 9. Backtesting

#### Run Backtest
```http
POST /backtesting/run
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "strategy_id": "uuid-string",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000.00,
  "benchmark": "SPY"
}
```

**Response (202)**:
```json
{
  "backtest_id": "uuid-string",
  "status": "running",
  "estimated_completion": "2025-07-03T14:35:00Z"
}
```

#### Get Backtest Results
```http
GET /backtesting/results/{backtest_id}
Authorization: Bearer <jwt_token>
```

### 10. Watchlists

#### Create Watchlist
```http
POST /watchlists
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "name": "Tech Stocks",
  "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"],
  "alerts": [
    {
      "symbol": "AAPL",
      "condition": "price_above",
      "value": 155.00
    }
  ]
}
```

#### Get Watchlists
```http
GET /watchlists
Authorization: Bearer <jwt_token>
```

#### Add Symbol to Watchlist
```http
POST /watchlists/{watchlist_id}/symbols
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "symbol": "TSLA"
}
```

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('wss://ws.tradingplatform.com/v1');
ws.send(JSON.stringify({
  type: 'auth',
  token: 'jwt-token'
}));
```

### Real-time Price Updates
```javascript
// Subscribe to price updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'quotes',
  symbols: ['AAPL', 'MSFT']
}));

// Receive updates
{
  "type": "quote",
  "symbol": "AAPL",
  "price": 150.25,
  "timestamp": "2025-07-03T14:30:15Z"
}
```

### Trade Execution Updates
```javascript
// Subscribe to trade updates
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'trades'
}));

// Receive execution updates
{
  "type": "trade_update",
  "order_id": "uuid-string",
  "status": "filled",
  "fill_price": 150.25,
  "fill_quantity": 100,
  "timestamp": "2025-07-03T14:30:20Z"
}
```

## Rate Limits

### Standard Limits
- **Authentication**: 10 requests/minute
- **Market Data**: 1000 requests/minute
- **Trading**: 100 requests/minute
- **Predictions**: 50 requests/minute

### Enterprise Limits
- **All Endpoints**: 10,000 requests/minute
- **Custom limits available**

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "The provided symbol is not valid",
    "details": {
      "symbol": "INVALID",
      "valid_symbols": ["AAPL", "MSFT", "GOOGL"]
    },
    "timestamp": "2025-07-03T14:30:00Z",
    "request_id": "uuid-string"
  }
}
```

### Common Error Codes
- `UNAUTHORIZED`: Invalid or expired token
- `INSUFFICIENT_FUNDS`: Not enough buying power
- `INVALID_SYMBOL`: Symbol not found or not supported
- `MARKET_CLOSED`: Trading not available during market hours
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `BROKER_ERROR`: Error from broker API
- `PREDICTION_UNAVAILABLE`: ML model not available

## SDK Examples

### Python SDK
```python
from trading_platform import TradingClient

client = TradingClient(api_key='your_key')

# Get predictions
predictions = client.predictions.get('AAPL', timeframe='intraday')

# Place order
order = client.trading.place_order(
    symbol='AAPL',
    quantity=100,
    side='buy',
    order_type='market'
)
```

### JavaScript SDK
```javascript
import { TradingClient } from '@trading-platform/sdk';

const client = new TradingClient({ apiKey: 'your_key' });

// Get real-time quotes
const quote = await client.market.getQuote('AAPL');

// Subscribe to WebSocket updates
client.ws.subscribe('quotes', ['AAPL'], (data) => {
  console.log('Price update:', data);
});
```