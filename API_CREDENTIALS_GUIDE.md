# 🔑 API Credentials Setup Guide
## Real-time Market Data Providers for Indian Markets

### 📊 Current API Integrations

Based on the live market data service, here are the APIs you need to configure:

---

## 1. 🆓 **FREE APIs** (No Cost)

### **NSE India (Free)**
- **URL**: https://www.nseindia.com/api
- **Cost**: FREE
- **Rate Limit**: ~100 requests/minute
- **Coverage**: Indian stocks (NSE)
- **Setup**: No API key required
- **Status**: ✅ Already integrated

### **Yahoo Finance (Free)**
- **URL**: https://query1.finance.yahoo.com
- **Cost**: FREE
- **Rate Limit**: ~200 requests/minute
- **Coverage**: Global markets including Indian stocks (.NS suffix)
- **Setup**: No API key required
- **Status**: ✅ Already integrated

---

## 2. 💰 **PAID APIs** (Recommended for Production)

### **Alpha Vantage**
- **URL**: https://www.alphavantage.co
- **Free Tier**: 5 requests/minute, 500 requests/day
- **Paid Plans**: 
  - $49.99/month: 75 requests/minute
  - $149.99/month: 300 requests/minute
  - $499.99/month: 1200 requests/minute
- **Coverage**: Global markets, Indian stocks
- **Setup Required**: ✅ API Key needed
- **Environment Variable**: `ALPHA_VANTAGE_API_KEY`

### **Polygon.io**
- **URL**: https://polygon.io
- **Free Tier**: Limited historical data only
- **Paid Plans**:
  - $99/month: Real-time US markets
  - $199/month: Real-time + extended hours
  - Custom pricing for Indian markets
- **Coverage**: Primarily US markets, limited Indian coverage
- **Setup Required**: ✅ API Key needed
- **Environment Variable**: `POLYGON_API_KEY`

---

## 3. 🇮🇳 **RECOMMENDED INDIAN MARKET APIs**

### **Upstox API** (Highly Recommended)
- **URL**: https://upstox.com/developer
- **Cost**: FREE for market data with trading account
- **Rate Limit**: Generous limits
- **Coverage**: NSE, BSE real-time data
- **Features**: Live quotes, historical data, market depth
- **Setup**: Requires Upstox trading account + API registration

### **Zerodha Kite API** (Premium Choice)
- **URL**: https://kite.trade
- **Cost**: ₹2,000/month for API access
- **Rate Limit**: Very high limits
- **Coverage**: NSE, BSE, MCX, NCDEX
- **Features**: Real-time data, order placement, portfolio management
- **Setup**: Requires Zerodha trading account + API subscription

### **ICICI Breeze API**
- **URL**: https://www.icicidirect.com/apiuser
- **Cost**: FREE with ICICI trading account
- **Coverage**: NSE, BSE
- **Setup**: Requires ICICI Direct trading account

### **Angel One SmartAPI**
- **URL**: https://smartapi.angelbroking.com
- **Cost**: FREE with Angel One account
- **Coverage**: NSE, BSE, MCX
- **Setup**: Requires Angel One trading account

---

## 🔧 **Setup Instructions**

### Step 1: Environment Variables Setup

Create a `.env` file in your backend directory:

```bash
# Alpha Vantage (Optional - for additional data)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here

# Polygon.io (Optional - primarily for US markets)
POLYGON_API_KEY=your_polygon_key_here

# Indian Broker APIs (Choose one or more)
UPSTOX_API_KEY=your_upstox_api_key
UPSTOX_SECRET=your_upstox_secret

ZERODHA_API_KEY=your_zerodha_api_key
ZERODHA_SECRET=your_zerodha_secret

ICICI_BREEZE_API_KEY=your_icici_api_key
ICICI_BREEZE_SECRET=your_icici_secret

ANGEL_ONE_API_KEY=your_angel_api_key
ANGEL_ONE_CLIENT_ID=your_angel_client_id
```

### Step 2: Get API Keys

#### For Alpha Vantage (Optional):
1. Visit https://www.alphavantage.co/support/#api-key
2. Sign up for free account
3. Get your API key
4. Add to `.env` file

#### For Indian Broker APIs (Recommended):
1. **Upstox**: Open account → Developer Portal → Create App
2. **Zerodha**: Open account → Kite Connect → Subscribe (₹2,000/month)
3. **ICICI**: Open ICICI Direct account → API section
4. **Angel One**: Open account → SmartAPI registration

### Step 3: Update Service Configuration

The service will automatically detect and use available API keys based on environment variables.

---

## 📈 **Recommended Setup for Production**

### **Minimum Setup (FREE)**
- ✅ NSE India API (already working)
- ✅ Yahoo Finance (already working)
- ⭐ One Indian broker API (Upstox/ICICI - free with account)

### **Optimal Setup (₹2,000-5,000/month)**
- ✅ All free APIs above
- ⭐ Zerodha Kite API (₹2,000/month)
- ⭐ Alpha Vantage Basic Plan ($49.99/month)

### **Enterprise Setup (₹10,000+/month)**
- ✅ Multiple broker APIs for redundancy
- ⭐ Alpha Vantage Professional Plan
- ⭐ Direct exchange data feeds

---

## 🚨 **Important Notes**

1. **Trading Account Required**: Most Indian broker APIs require an active trading account
2. **KYC Compliance**: You'll need proper KYC documentation
3. **Rate Limits**: Free APIs have strict rate limits
4. **Data Quality**: Paid APIs provide more reliable, faster data
5. **Backup APIs**: Always configure multiple providers for redundancy

---

## 🎯 **Next Steps**

1. **Choose your API providers** based on budget and requirements
2. **Open required trading accounts** for Indian broker APIs
3. **Register for API access** with chosen providers
4. **Configure environment variables** in `.env` file
5. **Test the setup** using our monitoring tools

Would you like me to help you integrate any specific API provider?