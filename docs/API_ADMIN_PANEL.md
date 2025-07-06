# Admin Panel API Documentation

## Overview

The Admin Panel API provides comprehensive administrative control over the AI Trading Platform. It implements role-based access control (RBAC), comprehensive auditing, and enterprise-grade security features.

## Base URL
```
https://api.tradingplatform.com/admin
```

## Authentication

All admin API endpoints require Bearer token authentication with proper role-based permissions.

### Login
```http
POST /admin/auth/login
Content-Type: application/json

{
  "username": "admin@example.com",
  "password": "password123",
  "mfa_token": "123456"  // Optional, required if MFA enabled
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "admin": {
    "id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "role": "super_admin",
    "permissions": ["ALL"]
  },
  "session": {
    "id": "session-uuid",
    "expires_at": "2024-01-01T12:00:00Z"
  }
}
```

### Get Current Admin Info
```http
GET /admin/auth/me
Authorization: Bearer <token>
```

### Logout
```http
POST /admin/auth/logout
Authorization: Bearer <token>
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "success": false,
  "error": "PERMISSION_DENIED",
  "message": "Insufficient permissions for this action",
  "details": {
    "required_permission": "MANAGE_USERS",
    "current_role": "support_agent"
  }
}
```

## Rate Limiting

- **Rate Limit**: 60 requests per minute per IP
- **Headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Exceed Response**: `429 Too Many Requests`

## Security Headers

All requests should include:
- `Authorization: Bearer <token>` - Required for authentication
- `X-MFA-Token: <6-digit-code>` - Required for high-risk actions
- `X-Request-ID: <uuid>` - Optional, for request tracking

## User Management API

### Get Users
```http
GET /admin/users?page=1&limit=50&search=user@example.com&status=active
Authorization: Bearer <token>
```

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (max: 500)
- `search` (string): Search by email or username
- `status` (string): Filter by status (active, inactive)
- `subscription_tier` (string): Filter by subscription
- `sort_by` (string): Sort field (default: created_at)
- `sort_order` (string): asc or desc (default: desc)

**Response:**
```json
{
  "users": [
    {
      "id": "user-uuid",
      "email": "user@example.com",
      "username": "trader123",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "subscription_tier": "pro",
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1250,
    "pages": 25
  }
}
```

### Get User Details
```http
GET /admin/users/{user_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "profile": {
      "first_name": "John",
      "last_name": "Doe",
      "phone": "+1234567890",
      "country": "India"
    },
    "account": {
      "is_active": true,
      "email_verified": true,
      "kyc_status": "approved",
      "risk_level": "medium"
    },
    "statistics": {
      "total_trades": 156,
      "win_rate": 68.5,
      "total_pnl": 15000.00,
      "days_active": 45
    }
  },
  "subscriptions": [
    {
      "id": "sub-uuid",
      "plan_name": "Pro Plan",
      "status": "active",
      "started_at": "2024-01-01T00:00:00Z",
      "expires_at": "2024-02-01T00:00:00Z"
    }
  ],
  "recent_trades": [
    {
      "id": "trade-uuid",
      "symbol": "RELIANCE",
      "side": "buy",
      "quantity": 100,
      "price": 2500.00,
      "pnl": 150.00,
      "executed_at": "2024-01-15T14:30:00Z"
    }
  ],
  "portfolio": {
    "total_value": 250000.00,
    "cash_balance": 50000.00,
    "positions": 12,
    "unrealized_pnl": 2500.00
  }
}
```

### Update User Status
```http
PUT /admin/users/{user_id}/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "is_active": false,
  "reason": "Suspicious trading activity detected"
}
```

### Reset User Password
```http
POST /admin/users/{user_id}/reset-password
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Password reset email sent to user",
  "temp_password": "temp123456",
  "expires_at": "2024-01-16T12:00:00Z"
}
```

## Subscription Management API

### Get Subscription Plans
```http
GET /admin/subscriptions/plans
Authorization: Bearer <token>
```

**Response:**
```json
{
  "plans": [
    {
      "id": "plan-uuid",
      "name": "Basic Plan",
      "description": "Perfect for beginners",
      "price": 2999.00,
      "currency": "INR",
      "billing_cycle": "monthly",
      "features": {
        "auto_trading": false,
        "api_calls": 1000,
        "real_time_data": true,
        "advanced_charts": false
      },
      "limits": {
        "auto_trading_limit": 0,
        "api_calls_limit": 1000,
        "concurrent_strategies": 1
      },
      "is_active": true,
      "trial_days": 7
    }
  ]
}
```

### Create Subscription Plan
```http
POST /admin/subscriptions/plans
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Enterprise Plan",
  "description": "For institutional traders",
  "price": 29999.00,
  "currency": "INR",
  "billing_cycle": "monthly",
  "features": {
    "auto_trading": true,
    "api_calls": 100000,
    "real_time_data": true,
    "advanced_charts": true,
    "custom_indicators": true,
    "priority_support": true
  },
  "limits": {
    "auto_trading_limit": 1000,
    "api_calls_limit": 100000,
    "concurrent_strategies": 10
  },
  "trial_days": 14,
  "is_active": true
}
```

### Get User Subscriptions
```http
GET /admin/subscriptions/users?page=1&limit=50&plan_name=Pro&status=active
Authorization: Bearer <token>
```

### Change User Subscription
```http
POST /admin/users/{user_id}/change-plan
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_plan_id": "plan-uuid",
  "reason": "User requested upgrade",
  "apply_immediately": true,
  "prorate": true
}
```

### Cancel User Subscription
```http
POST /admin/users/{user_id}/cancel
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "User requested cancellation",
  "immediate": false,
  "refund_amount": 1500.00
}
```

## Analytics API

### Dashboard Overview
```http
GET /admin/dashboard/overview
Authorization: Bearer <token>
```

**Response:**
```json
{
  "overview": {
    "users": {
      "total": 15000,
      "new_today": 45,
      "active_today": 3200
    },
    "revenue": {
      "daily": 125000.00,
      "mrr": 3500000.00,
      "arr": 42000000.00
    },
    "trading": {
      "trades_today": 8500,
      "success_rate": 68.5,
      "total_volume": 25000000.00
    },
    "system": {
      "api_response_time": 125.5,
      "active_sessions": 1200,
      "system_status": "healthy"
    },
    "support": {
      "pending_tickets": 12,
      "unread_notifications": 3
    }
  }
}
```

### User Analytics
```http
GET /admin/analytics/users?days=30
Authorization: Bearer <token>
```

**Response:**
```json
{
  "analytics": [
    {
      "date": "2024-01-01",
      "total_users": 14500,
      "new_registrations": 25,
      "active_users_daily": 3100,
      "churned_users": 5
    }
  ]
}
```

### Revenue Analytics
```http
GET /admin/analytics/revenue?days=30
Authorization: Bearer <token>
```

### Trading Analytics
```http
GET /admin/analytics/trading?days=30
Authorization: Bearer <token>
```

## Support Ticket Management

### Get Support Tickets
```http
GET /admin/tickets?page=1&limit=50&status=open&priority=high&assigned_to_me=true
Authorization: Bearer <token>
```

**Response:**
```json
{
  "tickets": [
    {
      "id": "ticket-uuid",
      "ticket_number": "TKT-2024-001",
      "subject": "Unable to place trades",
      "status": "open",
      "priority": "high",
      "category": "technical",
      "created_at": "2024-01-15T10:00:00Z",
      "assigned_admin": "support_agent_1",
      "user": {
        "id": "user-uuid",
        "email": "user@example.com",
        "tier": "pro"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 156,
    "pages": 4
  }
}
```

### Get Ticket Details
```http
GET /admin/tickets/{ticket_id}
Authorization: Bearer <token>
```

### Update Ticket
```http
PUT /admin/tickets/{ticket_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "in_progress",
  "priority": "high",
  "assigned_admin_id": "admin-uuid",
  "internal_notes": "Escalating to technical team"
}
```

### Add Ticket Response
```http
POST /admin/tickets/{ticket_id}/responses
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Thank you for contacting support. We're investigating the issue.",
  "is_internal": false,
  "attachments": ["file1.pdf", "screenshot.png"]
}
```

## Trading Operations API

### Get Trading Status
```http
GET /admin/trading/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "trading_engine": {
    "status": "active",
    "uptime": "5 days, 12 hours",
    "last_restart": "2024-01-10T08:00:00Z"
  },
  "market_data": {
    "status": "connected",
    "latency": 15.5,
    "feeds_active": 12
  },
  "brokers": [
    {
      "name": "Zerodha",
      "status": "connected",
      "api_health": "good",
      "rate_limit_remaining": 2850
    }
  ],
  "risk_management": {
    "global_limits": {
      "max_position_size": 10000000.00,
      "max_daily_loss": 500000.00
    },
    "current_exposure": 2500000.00,
    "risk_utilization": 25.0
  }
}
```

### Emergency Trading Halt
```http
POST /admin/trading/emergency-halt
Authorization: Bearer <token>
X-MFA-Token: 123456
Content-Type: application/json

{
  "reason": "Market anomaly detected",
  "halt_duration": 3600,
  "notify_users": true
}
```

### Update Risk Parameters
```http
PUT /admin/trading/risk-parameters
Authorization: Bearer <token>
Content-Type: application/json

{
  "global_limits": {
    "max_position_size": 15000000.00,
    "max_daily_loss": 750000.00,
    "max_leverage": 5.0
  },
  "user_limits": {
    "basic_plan": {
      "max_position_size": 100000.00,
      "max_daily_loss": 5000.00
    },
    "pro_plan": {
      "max_position_size": 500000.00,
      "max_daily_loss": 25000.00
    }
  }
}
```

## System Administration

### Get System Health
```http
GET /admin/system/health
Authorization: Bearer <token>
```

**Response:**
```json
{
  "overall_status": "healthy",
  "services": [
    {
      "name": "api_server",
      "status": "healthy",
      "response_time": 125.5,
      "cpu_usage": 45.2,
      "memory_usage": 68.1
    },
    {
      "name": "database",
      "status": "healthy",
      "connections_active": 45,
      "query_time_avg": 15.2
    },
    {
      "name": "trading_engine",
      "status": "healthy",
      "orders_processed": 8500,
      "error_rate": 0.05
    }
  ],
  "metrics": {
    "api_requests_total": 156000,
    "api_error_rate": 0.12,
    "websocket_connections": 1200,
    "background_jobs_pending": 5
  }
}
```

### Get System Metrics
```http
GET /admin/system/metrics?hours=24
Authorization: Bearer <token>
```

### Feature Flags
```http
GET /admin/system/feature-flags
Authorization: Bearer <token>
```

```http
PUT /admin/system/feature-flags/{flag_name}
Authorization: Bearer <token>
Content-Type: application/json

{
  "is_enabled": true,
  "target_percentage": 50.0,
  "target_user_segments": ["pro_users", "beta_testers"]
}
```

## Audit and Compliance

### Get Audit Logs
```http
GET /admin/audit/logs?page=1&limit=100&admin_id=uuid&action=USER_SUSPENDED&severity=WARNING
Authorization: Bearer <token>
```

**Response:**
```json
{
  "logs": [
    {
      "id": "log-uuid",
      "admin": {
        "id": "admin-uuid",
        "username": "admin1",
        "role": "business_admin"
      },
      "action": "USER_SUSPENDED",
      "category": "USER_MANAGEMENT",
      "description": "Suspended user due to policy violation",
      "resource_type": "User",
      "resource_id": "user-uuid",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "severity": "WARNING",
      "before_state": {
        "is_active": true
      },
      "after_state": {
        "is_active": false,
        "suspension_reason": "Policy violation"
      },
      "timestamp": "2024-01-15T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 100,
    "total": 5000,
    "pages": 50
  }
}
```

### Export Audit Data
```http
POST /admin/audit/export
Authorization: Bearer <token>
Content-Type: application/json

{
  "date_from": "2024-01-01T00:00:00Z",
  "date_to": "2024-01-31T23:59:59Z",
  "format": "csv",
  "include_fields": ["admin", "action", "timestamp", "ip_address"],
  "filters": {
    "severity": ["WARNING", "ERROR"],
    "category": ["USER_MANAGEMENT", "TRADING"]
  }
}
```

## Notifications API

### Get Admin Notifications
```http
GET /admin/notifications?page=1&limit=20&is_read=false&type=security
Authorization: Bearer <token>
```

### Mark Notification as Read
```http
PUT /admin/notifications/{notification_id}/read
Authorization: Bearer <token>
```

### Create System Notification
```http
POST /admin/notifications
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Scheduled Maintenance",
  "message": "System maintenance scheduled for 2024-01-20 02:00 UTC",
  "type": "info",
  "priority": "normal",
  "is_global": true,
  "target_roles": ["all"],
  "expires_at": "2024-01-20T06:00:00Z"
}
```

## Data Export API

### Export Users
```http
POST /admin/export/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "format": "csv",
  "date_from": "2024-01-01",
  "date_to": "2024-01-31",
  "include_fields": ["email", "created_at", "subscription_tier", "last_login"],
  "filters": {
    "subscription_tier": ["pro", "enterprise"],
    "is_active": true
  }
}
```

### Export Trading Data
```http
POST /admin/export/trades
Authorization: Bearer <token>
Content-Type: application/json

{
  "format": "excel",
  "date_from": "2024-01-01",
  "date_to": "2024-01-31",
  "include_pnl": true,
  "group_by": "user"
}
```

## Webhook Management

### Get Webhooks
```http
GET /admin/webhooks
Authorization: Bearer <token>
```

### Create Webhook
```http
POST /admin/webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "User Registration Webhook",
  "url": "https://external-system.com/webhook",
  "events": ["user.created", "user.subscription.changed"],
  "secret": "webhook_secret_key",
  "is_active": true
}
```

## Permission Levels

### Super Admin (Level 5)
- Full access to all endpoints
- Can create/modify other admin accounts
- Can change system configurations
- Can execute emergency procedures

### System Admin (Level 4)
- Infrastructure and system management
- Database administration (limited)
- Security incident response
- Cannot modify core business logic

### Business Admin (Level 3)
- User and subscription management
- Revenue analytics
- Business intelligence
- Support ticket escalation

### Trading Manager (Level 2)
- Trading operations control
- Risk management
- Broker integrations
- Trading analytics

### Support Manager (Level 2)
- Support ticket management
- User communication
- Limited user account modifications
- Team performance monitoring

### Financial Manager (Level 2)
- Financial analytics
- Payment processing
- Refund management
- Revenue reporting

### Support Agent (Level 1)
- Assigned ticket management
- Basic user information access
- Knowledge base access
- Limited actions

### Content Manager (Level 1)
- CMS and content management
- SEO tools
- Marketing campaigns
- No user data access

### Data Analyst (Level 1)
- Analytics dashboards
- Report generation
- Data export (aggregated)
- No individual user data

### Security Analyst (Level 1)
- Security monitoring
- Audit log access
- Incident investigation
- No user account modifications

## Error Codes

- `AUTHENTICATION_REQUIRED`: Missing or invalid authentication
- `PERMISSION_DENIED`: Insufficient permissions
- `MFA_REQUIRED`: Multi-factor authentication required
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `IP_RESTRICTED`: IP address not allowed
- `SESSION_EXPIRED`: Session has expired
- `ACCOUNT_LOCKED`: Admin account locked
- `INVALID_MFA`: Invalid MFA token
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `VALIDATION_ERROR`: Input validation failed
- `SYSTEM_ERROR`: Internal system error

## Security Best Practices

1. **Always use HTTPS** in production
2. **Rotate JWT secrets** regularly
3. **Implement IP whitelisting** for admin access
4. **Enable MFA** for all high-privilege accounts
5. **Monitor audit logs** for suspicious activity
6. **Use principle of least privilege** for role assignments
7. **Regularly review** admin user permissions
8. **Set up alerts** for critical admin actions

## Rate Limits

| Endpoint Category | Limit | Window |
|------------------|--------|---------|
| Authentication | 10 requests | 5 minutes |
| User Management | 100 requests | 1 minute |
| Analytics | 60 requests | 1 minute |
| Trading Operations | 30 requests | 1 minute |
| System Administration | 20 requests | 1 minute |
| Exports | 5 requests | 5 minutes |

## Support

For API support or questions:
- **Email**: admin-api-support@tradingplatform.com
- **Documentation**: https://docs.tradingplatform.com/admin-api
- **Status Page**: https://status.tradingplatform.com