# Auto Trading API Documentation

## Overview

The Auto Trading API provides comprehensive endpoints for managing AI-powered automatic trading functionality. This includes enabling/disabling auto-trading, configuring trading modes, monitoring trade execution, and generating detailed reports.

## Base URL
```
/v1/auto-trading
```

## Authentication
All endpoints require authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Auto Trading Management Endpoints

### GET /v1/auto-trading/status
Get current auto-trading status and statistics for the authenticated user.

**Response:**
```json
{
  "enabled": true,
  "mode": "conservative",
  "subscription_plan": "pro",
  "daily_limit": 50,
  "trades_today": 12,
  "remaining_trades": 38,
  "successful_trades_today": 10,
  "is_market_open": true,
  "has_active_session": true,
  "primary_broker_connected": true
}
```

### POST /v1/auto-trading/enable
Enable auto-trading with specified settings.

**Request Body:**
```json
{
  "enabled": true,
  "mode": "conservative"
}
```

**Response:**
```json
{
  "message": "Auto-trading enabled successfully",
  "enabled": true,
  "mode": "conservative"
}
```

**Trading Modes:**
- `conservative`: 80% min confidence, 2% min return, 5% max position size
- `moderate`: 70% min confidence, 1.5% min return, 8% max position size  
- `aggressive`: 60% min confidence, 1% min return, 10% max position size

### POST /v1/auto-trading/disable
Disable auto-trading for the authenticated user.

**Response:**
```json
{
  "message": "Auto-trading disabled successfully",
  "enabled": false
}
```

### PUT /v1/auto-trading/settings
Update auto-trading configuration.

**Request Body:**
```json
{
  "enabled": true,
  "mode": "moderate"
}
```

**Response:**
```json
{
  "message": "Auto-trading settings updated successfully",
  "enabled": true,
  "mode": "moderate"
}
```

### GET /v1/auto-trading/trades
Get auto-trading history with optional filters.

**Query Parameters:**
- `limit` (integer): Number of trades to return (default: 50, max: 200)
- `offset` (integer): Number of trades to skip (default: 0)
- `status_filter` (string): Filter by status (`executed`, `failed`, `pending`, `cancelled`)
- `symbol` (string): Filter by symbol (e.g., `RELIANCE`)
- `start_date` (string): Start date in ISO format
- `end_date` (string): End date in ISO format

**Response:**
```json
[
  {
    "id": "uuid",
    "date": "2025-01-15",
    "time": "10:30:45",
    "symbol": "RELIANCE",
    "side": "buy",
    "quantity": 10,
    "price": 2500.0,
    "executed_price": 2501.5,
    "total_value": 25000.0,
    "confidence": 0.85,
    "expected_return": 0.025,
    "realized_pnl": 150.0,
    "status": "executed",
    "reason": "ml_prediction",
    "execution_time": "2025-01-15T10:30:47Z"
  }
]
```

### GET /v1/auto-trading/analytics
Get auto-trading analytics and performance metrics.

**Query Parameters:**
- `days` (integer): Number of days to analyze (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "total_trades": 45,
  "successful_trades": 38,
  "failed_trades": 7,
  "success_rate": 84.44,
  "total_pnl": 12500.50,
  "average_return": 2.1,
  "average_confidence": 78.5,
  "most_traded_symbols": [
    { "symbol": "RELIANCE", "count": 12 },
    { "symbol": "TCS", "count": 8 }
  ],
  "daily_trade_count": [
    { "date": "2025-01-15", "count": 3 },
    { "date": "2025-01-16", "count": 5 }
  ]
}
```

### GET /v1/auto-trading/market-status
Get current market status for auto-trading.

**Response:**
```json
{
  "is_market_open": true,
  "market_hours": {
    "nse": {
      "open": "09:15",
      "close": "15:30",
      "timezone": "Asia/Kolkata"
    },
    "bse": {
      "open": "09:15",
      "close": "15:30", 
      "timezone": "Asia/Kolkata"
    }
  },
  "message": "Market is open"
}
```

## Manual Intervention Endpoints

### POST /v1/auto-trading/emergency-stop
🚨 **Emergency stop all auto-trading activity immediately**

**Request Body:**
```json
{
  "reason": "Market volatility - manual intervention"
}
```

**Response:**
```json
{
  "message": "Emergency stop executed successfully",
  "reason": "Market volatility - manual intervention",
  "timestamp": "2025-01-15T14:30:00Z",
  "status": "stopped"
}
```

**Important Notes:**
- Immediately disables auto-trading for the user
- Cancels all pending auto-trades
- Stops active trading session
- Sends emergency notification to user
- Cannot be undone - must manually re-enable trading

### POST /v1/auto-trading/pause
⏸️ **Temporarily pause auto-trading for a specified duration**

**Request Body:**
```json
{
  "duration_minutes": 30,
  "reason": "Manual pause for market review"
}
```

**Response:**
```json
{
  "message": "Auto-trading paused for 30 minutes",
  "duration_minutes": 30,
  "reason": "Manual pause for market review",
  "paused_until": "2025-01-15T15:00:00Z",
  "status": "paused"
}
```

**Parameters:**
- `duration_minutes`: Duration in minutes (1-1440, max 24 hours)
- `reason`: Optional reason for pause

**Important Notes:**
- Auto-trading will automatically resume after the specified duration
- Can be manually resumed before expiration
- Does not cancel existing trades, only prevents new ones
- Preserves trading session and settings

### POST /v1/auto-trading/resume
▶️ **Resume auto-trading after manual pause**

**Response:**
```json
{
  "message": "Auto-trading resumed successfully",
  "timestamp": "2025-01-15T14:45:00Z",
  "status": "active"
}
```

**Important Notes:**
- Only works if trading was previously paused
- Immediately resumes trade execution if market is open
- Requires user to still have enabled auto-trading
- Checks all prerequisites (broker connection, subscription, etc.)

## Reports API Endpoints

### GET /v1/reports/auto-trades/summary
Get summary of auto-executed trades for a specific period.

**Query Parameters:**
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)

**Response:**
```json
{
  "period_start": "2025-01-01",
  "period_end": "2025-01-15", 
  "total_trades": 45,
  "successful_trades": 38,
  "failed_trades": 7,
  "total_volume": 125000.0,
  "total_pnl": 5250.75,
  "success_rate": 84.44,
  "average_trade_size": 2777.78,
  "best_performing_symbol": "RELIANCE",
  "worst_performing_symbol": "ICICIBANK"
}
```

### POST /v1/reports/auto-trades/detailed
Get detailed auto-trades report with advanced filters.

**Request Body:**
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-15",
  "symbols": ["RELIANCE", "TCS"],
  "status": "executed",
  "trade_type": "auto",
  "min_amount": 1000.0,
  "max_amount": 50000.0
}
```

**Response:**
```json
{
  "summary": {
    "period_start": "2025-01-01",
    "period_end": "2025-01-15",
    "total_trades": 25,
    "successful_trades": 22,
    "failed_trades": 3,
    "total_volume": 85000.0,
    "total_pnl": 3250.50,
    "success_rate": 88.0,
    "average_trade_size": 3400.0,
    "best_performing_symbol": "RELIANCE",
    "worst_performing_symbol": "TCS"
  },
  "trades": [
    {
      "id": "uuid",
      "date": "2025-01-15",
      "time": "10:30:45",
      "symbol": "RELIANCE",
      "side": "buy",
      "quantity": 10,
      "price": 2500.0,
      "executed_price": 2501.5,
      "total_value": 25000.0,
      "confidence": 0.85,
      "expected_return": 0.025,
      "realized_pnl": 150.0,
      "status": "executed",
      "reason": "ml_prediction",
      "execution_time": "2025-01-15T10:30:47Z"
    }
  ],
  "daily_breakdown": [
    {
      "date": "2025-01-15",
      "total_trades": 3,
      "successful_trades": 3,
      "total_volume": 15000.0,
      "total_pnl": 450.0
    }
  ],
  "symbol_breakdown": [
    {
      "symbol": "RELIANCE",
      "total_trades": 12,
      "successful_trades": 11,
      "total_volume": 45000.0,
      "total_pnl": 1250.0,
      "avg_confidence": 0.82
    }
  ]
}
```

### GET /v1/reports/auto-trades/export
Export auto-trades report in CSV or JSON format.

**Query Parameters:**
- `format` (string): Export format (`csv` or `json`)
- `start_date` (string): Start date (YYYY-MM-DD)
- `end_date` (string): End date (YYYY-MM-DD)
- `symbols` (string): Comma-separated symbols
- `status` (string): Filter by status

**Response:**
Returns a downloadable file in the requested format.

### GET /v1/reports/eod-summary
Get end-of-day trading summary.

**Query Parameters:**
- `trade_date` (string): Date for summary (YYYY-MM-DD, defaults to today)

**Response:**
```json
{
  "date": "2025-01-15",
  "auto_trading": {
    "total_trades": 8,
    "executed_trades": 7,
    "failed_trades": 1,
    "total_volume": 35000.0,
    "realized_pnl": 1250.50,
    "success_rate": 87.5,
    "symbols_traded": ["RELIANCE", "TCS", "INFY"]
  },
  "manual_trading": {
    "total_trades": 3,
    "total_volume": 15000.0,
    "estimated_pnl": 450.0
  },
  "overall": {
    "total_trades": 11,
    "total_volume": 50000.0,
    "total_pnl": 1700.50
  },
  "generated_at": "2025-01-15T15:45:00Z"
}
```

### GET /v1/reports/performance-metrics
Get comprehensive performance metrics.

**Query Parameters:**
- `period_days` (integer): Analysis period in days (default: 30)

**Response:**
```json
{
  "period_days": 30,
  "total_trades": 45,
  "metrics": {
    "total_return": 5250.75,
    "average_return_per_trade": 116.68,
    "win_rate": 84.44,
    "average_win": 185.50,
    "average_loss": -75.25,
    "profit_factor": 2.47,
    "average_confidence": 78.5,
    "best_trade": 650.0,
    "worst_trade": -125.0,
    "total_winning_trades": 38,
    "total_losing_trades": 7
  }
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Error message description",
  "error": {
    "code": "ERROR_CODE",
    "message": "Detailed error message"
  }
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (invalid or missing token)
- `403`: Forbidden (insufficient permissions or subscription)
- `404`: Not Found
- `500`: Internal Server Error

## Subscription Requirements

Auto-trading features require active subscriptions:

| Plan | Daily Trade Limit | Auto Trading | Advanced Features |
|------|------------------|--------------|-------------------|
| Free | 0 | ❌ | Market data only |
| Basic | 10 | ✅ | Basic strategies |
| Pro | 50 | ✅ | Advanced ML strategies |
| Enterprise | 1000 | ✅ | Custom strategies, API access |

## Rate Limits

- Auto-trading status: 60 requests/minute
- Trade history: 30 requests/minute  
- Reports generation: 10 requests/minute
- Export operations: 5 requests/minute

## WebSocket Events

Real-time auto-trading events are available via WebSocket:

```javascript
// Subscribe to auto-trading events
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'auto_trading',
  user_id: 'user_uuid'
}));

// Event examples
{
  "type": "trade_executed",
  "data": {
    "trade_id": "uuid",
    "symbol": "RELIANCE", 
    "side": "buy",
    "quantity": 10,
    "price": 2500.0,
    "timestamp": "2025-01-15T10:30:47Z"
  }
}

{
  "type": "status_update",
  "data": {
    "enabled": true,
    "trades_today": 13,
    "remaining_trades": 37
  }
}
```

## SDK Integration

### Python SDK Example
```python
from trading_platform_sdk import AutoTradingClient

client = AutoTradingClient(api_key="your_api_key")

# Enable auto trading
client.enable_auto_trading(mode="conservative")

# Get status
status = client.get_status()
print(f"Trades today: {status.trades_today}")

# Get reports
report = client.get_detailed_report(
    start_date="2025-01-01",
    end_date="2025-01-15"
)
```

### JavaScript SDK Example
```javascript
import { AutoTradingAPI } from '@trading-platform/sdk';

const api = new AutoTradingAPI({ apiKey: 'your_api_key' });

// Enable auto trading
await api.enableAutoTrading({ mode: 'moderate' });

// Get analytics
const analytics = await api.getAnalytics({ days: 30 });
console.log(`Success rate: ${analytics.success_rate}%`);
```

## Testing

Use the sandbox environment for testing:
- Base URL: `https://sandbox-api.tradingplatform.com`
- All endpoints support the same functionality with simulated data
- No real trades are executed in sandbox mode