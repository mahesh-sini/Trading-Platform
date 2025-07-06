"""
Performance testing with Locust for Trading Platform API
"""

import random
from locust import HttpUser, task, between
import json


class TradingPlatformUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login user and get auth token"""
        self.auth_token = None
        self.user_id = None
        self.login()
    
    def login(self):
        """Authenticate user"""
        response = self.client.post("/auth/login", json={
            "email": f"test{random.randint(1, 1000)}@example.com",
            "password": "testpassword123"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_id = data.get("user_id")
            self.client.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })
    
    @task(5)
    def get_portfolio(self):
        """Get user portfolio"""
        if self.auth_token:
            self.client.get(f"/portfolio/{self.user_id}")
    
    @task(5)
    def get_positions(self):
        """Get user positions"""
        if self.auth_token:
            self.client.get(f"/positions/{self.user_id}")
    
    @task(3)
    def get_market_data(self):
        """Get market data for a symbol"""
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA"]
        symbol = random.choice(symbols)
        self.client.get(f"/market/quote/{symbol}")
    
    @task(3)
    def get_historical_data(self):
        """Get historical data"""
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        symbol = random.choice(symbols)
        timeframe = random.choice(["1m", "5m", "15m", "1h", "1d"])
        self.client.get(f"/market/history/{symbol}?timeframe={timeframe}&limit=100")
    
    @task(2)
    def get_orders(self):
        """Get user orders"""
        if self.auth_token:
            self.client.get(f"/orders/{self.user_id}")
    
    @task(1)
    def place_order(self):
        """Place a trading order"""
        if self.auth_token:
            symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
            order_data = {
                "symbol": random.choice(symbols),
                "side": random.choice(["buy", "sell"]),
                "order_type": random.choice(["market", "limit"]),
                "quantity": random.randint(1, 100),
                "price": round(random.uniform(100, 300), 2)
            }
            
            response = self.client.post(f"/orders/{self.user_id}", json=order_data)
            
            # Cancel order immediately to avoid affecting real trading
            if response.status_code == 201:
                order_id = response.json().get("id")
                if order_id:
                    self.client.delete(f"/orders/{self.user_id}/{order_id}")
    
    @task(2)
    def get_alerts(self):
        """Get user alerts"""
        if self.auth_token:
            self.client.get(f"/alerts/{self.user_id}")
    
    @task(1)
    def get_strategy_performance(self):
        """Get strategy performance"""
        if self.auth_token:
            self.client.get(f"/strategies/{self.user_id}/performance")
    
    @task(2)
    def get_news(self):
        """Get financial news"""
        params = {
            "limit": random.randint(10, 50),
            "category": random.choice(["earnings", "market", "economic", "all"])
        }
        self.client.get("/news", params=params)
    
    @task(1)
    def get_technical_indicators(self):
        """Get technical indicators"""
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        symbol = random.choice(symbols)
        indicator = random.choice(["sma", "ema", "rsi", "macd", "bollinger"])
        
        self.client.get(f"/market/indicators/{symbol}/{indicator}")
    
    @task(1)
    def search_symbols(self):
        """Search for symbols"""
        queries = ["Apple", "Tesla", "Microsoft", "Google", "Amazon", "NVIDIA"]
        query = random.choice(queries)
        self.client.get(f"/market/search?q={query}")


class AdminUser(HttpUser):
    """Admin user with higher privileges"""
    wait_time = between(2, 5)
    weight = 1  # Lower weight for admin users
    
    def on_start(self):
        """Login as admin"""
        self.auth_token = None
        self.login_admin()
    
    def login_admin(self):
        """Authenticate admin user"""
        response = self.client.post("/auth/login", json={
            "email": "admin@tradingplatform.com",
            "password": "adminpassword123"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.auth_token}"
            })
    
    @task(3)
    def get_system_metrics(self):
        """Get system metrics"""
        if self.auth_token:
            self.client.get("/admin/metrics")
    
    @task(2)
    def get_all_users(self):
        """Get all users (admin only)"""
        if self.auth_token:
            self.client.get("/admin/users?page=1&limit=20")
    
    @task(2)
    def get_trading_analytics(self):
        """Get trading analytics"""
        if self.auth_token:
            self.client.get("/admin/analytics/trading")
    
    @task(1)
    def get_system_health(self):
        """Check system health"""
        if self.auth_token:
            self.client.get("/admin/health")


class WebSocketUser(HttpUser):
    """User that simulates WebSocket connections"""
    wait_time = between(5, 10)
    weight = 2
    
    @task
    def simulate_websocket_activity(self):
        """Simulate WebSocket connection activity"""
        # This simulates the load that WebSocket connections would put on the server
        # In a real test, you would use actual WebSocket connections
        
        # Subscribe to real-time data
        symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
        for symbol in random.sample(symbols, 3):
            self.client.get(f"/market/quote/{symbol}")
        
        # Simulate real-time updates
        self.client.get("/market/summary")
        
        # Wait to simulate holding connection
        import time
        time.sleep(random.uniform(1, 3))