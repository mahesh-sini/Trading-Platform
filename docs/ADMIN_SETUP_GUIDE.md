# Admin Panel Setup and Configuration Guide

## 🔐 Initial Admin Access

### Default Super Admin Credentials
**⚠️ CRITICAL SECURITY INFORMATION ⚠️**

Upon first deployment, the system automatically creates a Super Admin account with the following credentials:

```
Username: superadmin
Email: admin@tradingplatform.dev
Password: Admin123!@#ChangeMe
```

**🚨 IMPORTANT: Change this password immediately after first login!**

### First Login Steps

1. **Access Admin Panel**:
   ```
   URL: https://yourdomain.com/admin/login
   Username: superadmin
   Password: Admin123!@#ChangeMe
   ```

2. **Immediate Actions Required**:
   - Change the default password
   - Update email address to your actual admin email
   - Enable MFA (Multi-Factor Authentication)
   - Review and configure IP restrictions
   - Set up additional admin users

## 🎛️ System Configuration Setup

### Step 1: Configure System APIs

The admin panel includes a **System Configuration** section for managing all platform-level APIs. These APIs enable core features like charts, live prices, predictions, and news feeds.

#### Access System Configuration:
1. Login to Admin Panel
2. Navigate to **"System Configuration"** in sidebar
3. Go to **"API Management"** tab

#### Required API Categories:

### 📊 Market Data APIs (Essential for Charts & Prices)

#### Alpha Vantage (Recommended)
```
Provider: alpha_vantage
Display Name: Alpha Vantage Market Data
API Key: [Your Alpha Vantage API Key]
Base URL: https://www.alphavantage.co/query
Rate Limit: 5 requests/minute (free), 500/minute (paid)
Plan Type: free/premium
Features: Real-time quotes, historical data, technical indicators
```

#### Yahoo Finance (Free Backup)
```
Provider: yahoo_finance
Display Name: Yahoo Finance
API Key: [Not required for basic usage]
Base URL: https://query1.finance.yahoo.com
Rate Limit: 2000/hour
Plan Type: free
Features: Basic price data, limited historical data
```

#### Polygon.io (Professional)
```
Provider: polygon
Display Name: Polygon.io
API Key: [Your Polygon API Key]
Base URL: https://api.polygon.io
Rate Limit: 5/minute (free), unlimited (paid)
Plan Type: free/starter/developer/advanced
Features: Real-time data, options, forex, crypto
```

### 🇮🇳 Indian Market Data

#### NSE Official (If Available)
```
Provider: nse_official
Display Name: NSE Official Data
API Key: [NSE API Credentials]
Base URL: https://www.nseindia.com/api
Features: NSE stocks, F&O, indices, real-time data
```

#### Economic Times Markets
```
Provider: economic_times
Display Name: Economic Times Markets
API Key: [ET Markets API Key]
Features: Indian market news, stock data, economic indicators
```

### 🤖 AI/ML APIs (For Predictions)

#### OpenAI (Recommended)
```
Provider: openai
Display Name: OpenAI GPT
API Key: sk-[Your OpenAI API Key]
Base URL: https://api.openai.com/v1
Features: Market analysis, sentiment analysis, trading insights
Monthly Cost: ~$20-100 depending on usage
```

#### Anthropic Claude (Alternative)
```
Provider: anthropic
Display Name: Anthropic Claude
API Key: [Your Anthropic API Key]
Base URL: https://api.anthropic.com
Features: Advanced market analysis, risk assessment
```

### 📰 News & Sentiment APIs

#### News API
```
Provider: news_api
Display Name: News API
API Key: [Your News API Key]
Base URL: https://newsapi.org/v2
Features: Financial news, market sentiment, company news
```

#### Twitter API (Optional)
```
Provider: twitter_api
Display Name: Twitter API v2
API Key: [Your Twitter API Key]
Secret: [Your Twitter API Secret]
Features: Social sentiment, trending topics, market buzz
```

### 📧 Communication APIs

#### SendGrid (Email)
```
Provider: sendgrid
Display Name: SendGrid Email
API Key: SG.[Your SendGrid API Key]
Base URL: https://api.sendgrid.com/v3
Features: Transactional emails, notifications, alerts
```

#### Twilio (SMS)
```
Provider: twilio
Display Name: Twilio SMS
API Key: [Your Twilio Account SID]
Secret: [Your Twilio Auth Token]
Features: SMS alerts, 2FA, urgent notifications
```

## 🔧 API Configuration Process

### Adding New API Provider

1. **Navigate to System Configuration → API Management**
2. **Click "Add API" button**
3. **Fill in configuration**:
   ```json
   {
     "provider": "alpha_vantage",
     "display_name": "Alpha Vantage Market Data",
     "description": "Real-time and historical market data",
     "api_key": "YOUR_API_KEY_HERE",
     "base_url": "https://www.alphavantage.co/query",
     "rate_limit_per_minute": 5,
     "plan_type": "free",
     "is_enabled": true
   }
   ```
4. **Test Connection** - System will verify API health
5. **Save Configuration** - Credentials are automatically encrypted

### API Health Monitoring

The system automatically monitors all configured APIs:

- **Health Checks**: Every 5 minutes
- **Status Indicators**: 
  - 🟢 Active (API responding normally)
  - 🟡 Warning (Slow response or rate limits)
  - 🔴 Error (API down or authentication failed)
  - ⚪ Inactive (Disabled by admin)

### Feature Dependencies

Features automatically enable/disable based on API health:

| Feature | Required APIs | Optional APIs |
|---------|---------------|---------------|
| **Live Market Data** | alpha_vantage OR polygon OR yahoo_finance | finnhub, iex_cloud |
| **Indian Markets** | nse_official | bse_official, economic_times |
| **AI Predictions** | openai OR anthropic | google_ai, azure_ai |
| **News & Sentiment** | news_api | twitter_api, reddit_api |
| **Email Notifications** | sendgrid OR aws_ses | - |
| **SMS Alerts** | twilio | - |

## 👥 User Management

### Creating Additional Admin Users

1. **Navigate to User Management → Admin Users**
2. **Click "Add Admin User"**
3. **Select Role**:
   - **Super Admin** (Level 5): Full system access
   - **System Admin** (Level 4): Infrastructure management
   - **Business Admin** (Level 3): Business operations
   - **Trading Manager** (Level 2): Trading operations
   - **Support Manager** (Level 2): Customer service
   - **Financial Manager** (Level 2): Financial operations
   - **Support Agent** (Level 1): Limited support access

### Role-Based Permissions

#### Super Admin (Level 5)
- ✅ All system access
- ✅ Create/modify admin accounts
- ✅ System configuration
- ✅ Emergency controls
- ✅ Financial management
- ✅ Security settings

#### System Admin (Level 4)
- ✅ Infrastructure monitoring
- ✅ Database administration
- ✅ Security incident response
- ✅ API management
- ❌ User billing modifications
- ❌ Admin account creation

#### Business Admin (Level 3)
- ✅ User management
- ✅ Subscription management
- ✅ Business analytics
- ✅ Support escalation
- ❌ System infrastructure
- ❌ Security policies

#### Trading Manager (Level 2)
- ✅ Trading operations
- ✅ Risk management
- ✅ Broker integrations
- ✅ Trading analytics
- ❌ User billing
- ❌ System config

#### Support Manager/Financial Manager (Level 2)
- ✅ Department-specific full access
- ✅ Team management
- ✅ Reporting and analytics
- ❌ Other departments
- ❌ System administration

#### Support Agent/Specialists (Level 1)
- ✅ Assigned task management
- ✅ Basic information access
- ✅ Department tools
- ❌ User modifications
- ❌ System settings

## 🔒 Security Configuration

### Multi-Factor Authentication (MFA)

1. **Enable MFA for High-Level Roles**:
   - Super Admin: **Mandatory**
   - System Admin: **Mandatory**
   - Financial Manager: **Mandatory**
   - Others: **Recommended**

2. **Setup Process**:
   - Admin Profile → Security Settings
   - Enable MFA → Scan QR code with authenticator app
   - Enter verification code → Save

### IP Restrictions

Configure allowed IP ranges for admin access:

```json
{
  "admin_allowed_ip_ranges": [
    "203.192.xxx.xxx/32",    // Office IP
    "10.0.0.0/8",            // Private network
    "192.168.1.0/24"         // Local network
  ]
}
```

### Session Security

- **Session Timeout**: 8 hours (configurable per role)
- **Concurrent Sessions**: 3 max (configurable)
- **Automatic Logout**: On suspicious activity
- **Password Policy**: 
  - Minimum 12 characters
  - Must include: uppercase, lowercase, numbers, symbols
  - Cannot reuse last 5 passwords
  - Expires every 90 days (production)

## 📊 Monitoring & Alerts

### System Health Dashboard

Monitor overall system health:
- **API Status**: Real-time health of all configured APIs
- **Feature Status**: Which features are currently operational
- **Usage Metrics**: API call volumes and costs
- **Performance**: Response times and error rates

### Alert Configuration

Set up alerts for:
- **API Failures**: When critical APIs go down
- **High Usage**: When approaching rate limits
- **Security Events**: Failed login attempts, suspicious activity
- **System Performance**: High CPU, memory, or response times

### Cost Monitoring

Track API costs:
- **Daily Usage**: Track requests and costs per API
- **Monthly Budgets**: Set spending limits
- **Optimization**: Identify cost-saving opportunities
- **Forecasting**: Predict monthly costs based on usage trends

## 🚀 Deployment Checklist

### Pre-Production Setup

- [ ] Change default super admin password
- [ ] Configure primary market data API (Alpha Vantage recommended)
- [ ] Set up Indian market data (NSE/Economic Times)
- [ ] Configure AI/ML API for predictions (OpenAI recommended)
- [ ] Set up email notifications (SendGrid)
- [ ] Configure SMS alerts (Twilio) - optional
- [ ] Enable MFA for all admin accounts
- [ ] Set IP restrictions for admin access
- [ ] Test all API connections
- [ ] Verify all features are working
- [ ] Set up monitoring alerts
- [ ] Review and adjust rate limits

### Production Security

- [ ] Use strong environment-specific passwords
- [ ] Enable all security features
- [ ] Configure proper backup systems
- [ ] Set up log monitoring
- [ ] Enable audit trail retention
- [ ] Test disaster recovery procedures
- [ ] Document admin procedures
- [ ] Train admin team on security protocols

### API Key Security

- [ ] Store API keys in environment variables
- [ ] Use encrypted credential storage
- [ ] Rotate API keys regularly (quarterly)
- [ ] Monitor for API key exposure
- [ ] Set up alerts for unauthorized usage
- [ ] Use separate keys for dev/staging/production
- [ ] Document API key management procedures

## 📞 Support & Troubleshooting

### Common Issues

#### "API Connection Failed"
1. Verify API key is correct
2. Check API rate limits
3. Confirm base URL is accurate
4. Test API directly with curl/Postman
5. Check firewall/network restrictions

#### "Feature Not Available"
1. Check required APIs are configured and healthy
2. Verify feature is enabled in System Configuration
3. Check user subscription includes the feature
4. Review feature dependencies

#### "Admin Login Failed"
1. Verify username/password
2. Check account is not locked
3. Confirm IP address is allowed
4. Verify MFA code if enabled
5. Check admin account is active

### Emergency Procedures

#### Lost Super Admin Access
1. Access server directly
2. Connect to database
3. Reset password hash manually
4. Disable IP restrictions temporarily
5. Create new super admin account if needed

#### API Service Outage
1. Check API provider status pages
2. Switch to backup/alternative APIs
3. Notify users of reduced functionality
4. Monitor for service restoration
5. Update incident log

### Contact Information

- **System Administrator**: admin@tradingplatform.com
- **Emergency Contact**: +91-XXXX-XXXX-XXX
- **Technical Support**: support@tradingplatform.com
- **Security Issues**: security@tradingplatform.com

---

## 🔄 Regular Maintenance

### Daily Tasks
- [ ] Check system health dashboard
- [ ] Review API usage and costs
- [ ] Monitor security alerts
- [ ] Check failed login attempts

### Weekly Tasks
- [ ] Review admin audit logs
- [ ] Check API performance metrics
- [ ] Update system monitoring thresholds
- [ ] Review user support tickets

### Monthly Tasks
- [ ] Rotate API keys
- [ ] Review and update admin permissions
- [ ] Analyze cost optimization opportunities
- [ ] Update system documentation
- [ ] Security vulnerability assessment

### Quarterly Tasks
- [ ] Full security audit
- [ ] Admin access review
- [ ] API contract and pricing review
- [ ] Disaster recovery testing
- [ ] Update admin training materials

---

**Remember**: The admin panel is the control center for your entire trading platform. Proper configuration and security are critical for platform success and user trust. Always follow the principle of least privilege and maintain comprehensive audit trails.