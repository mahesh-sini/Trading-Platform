import httpx
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import os
import asyncio
from decimal import Decimal

logger = logging.getLogger(__name__)

class MarketDataClient:
    """Client for fetching live and historical market data"""
    
    def __init__(self):
        self.data_service_url = os.getenv("DATA_SERVICE_URL", "http://localhost:8002")
        self.timeout = httpx.Timeout(10.0)
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 30  # 30 seconds
        
    async def get_live_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live quote for a symbol"""
        try:
            # Check cache first
            cache_key = f"quote_{symbol}"
            if self._is_cached(cache_key):
                return self.cache[cache_key]["data"]
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.data_service_url}/market/quote/{symbol}",
                    params={"exchange": "NSE"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    quote_data = {
                        "symbol": symbol,
                        "price": float(data.get("regularMarketPrice", 0)),
                        "previous_close": float(data.get("regularMarketPreviousClose", 0)),
                        "change": float(data.get("regularMarketChange", 0)),
                        "change_percent": float(data.get("regularMarketChangePercent", 0)),
                        "volume": int(data.get("regularMarketVolume", 0)),
                        "bid": float(data.get("bid", 0)),
                        "ask": float(data.get("ask", 0)),
                        "bid_size": int(data.get("bidSize", 0)),
                        "ask_size": int(data.get("askSize", 0)),
                        "high": float(data.get("regularMarketDayHigh", 0)),
                        "low": float(data.get("regularMarketDayLow", 0)),
                        "open": float(data.get("regularMarketOpen", 0)),
                        "timestamp": datetime.utcnow().isoformat(),
                        "market_state": data.get("marketState", "UNKNOWN")
                    }
                    
                    # Cache the result
                    self._cache_data(cache_key, quote_data)
                    return quote_data
                    
                else:
                    logger.warning(f"Failed to get quote for {symbol}: {response.status_code}")
                    return await self._get_fallback_quote(symbol)
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout getting quote for {symbol}")
            return await self._get_fallback_quote(symbol)
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return await self._get_fallback_quote(symbol)
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1d",
        interval: str = "1m",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get historical market data"""
        try:
            params = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "exchange": "NSE"
            }
            
            if start_date:
                params["start"] = start_date.isoformat()
            if end_date:
                params["end"] = end_date.isoformat()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.data_service_url}/market/history",
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
                    logger.warning(f"Failed to get historical data for {symbol}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get market status"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.data_service_url}/market/status")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return await self._get_fallback_market_status()
                    
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return await self._get_fallback_market_status()
    
    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get quotes for multiple symbols"""
        try:
            # Use asyncio.gather for concurrent requests
            tasks = [self.get_live_quote(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            quotes = {}
            for i, symbol in enumerate(symbols):
                result = results[i]
                if isinstance(result, Exception):
                    logger.error(f"Error getting quote for {symbol}: {result}")
                    quotes[symbol] = None
                else:
                    quotes[symbol] = result
            
            return quotes
            
        except Exception as e:
            logger.error(f"Error getting multiple quotes: {e}")
            return {symbol: None for symbol in symbols}
    
    async def get_top_gainers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top gaining stocks"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.data_service_url}/market/gainers",
                    params={"limit": limit, "exchange": "NSE"}
                )
                
                if response.status_code == 200:
                    return response.json().get("data", [])
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting top gainers: {e}")
            return []
    
    async def get_top_losers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top losing stocks"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.data_service_url}/market/losers",
                    params={"limit": limit, "exchange": "NSE"}
                )
                
                if response.status_code == 200:
                    return response.json().get("data", [])
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting top losers: {e}")
            return []
    
    async def get_market_depth(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market depth/order book for a symbol"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.data_service_url}/market/depth/{symbol}",
                    params={"exchange": "NSE"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting market depth for {symbol}: {e}")
            return None
    
    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and still valid"""
        if key not in self.cache:
            return False
        
        cached_time = self.cache[key]["timestamp"]
        return (datetime.utcnow() - cached_time).seconds < self.cache_ttl
    
    def _cache_data(self, key: str, data: Any):
        """Cache data with timestamp"""
        self.cache[key] = {
            "data": data,
            "timestamp": datetime.utcnow()
        }
    
    async def _get_fallback_quote(self, symbol: str) -> Dict[str, Any]:
        """Get fallback quote data when primary source fails"""
        # Return basic mock data with current timestamp
        base_price = 100.0  # Default base price
        
        # Simple hash-based price generation for consistency
        symbol_hash = sum(ord(c) for c in symbol)
        price = base_price + (symbol_hash % 100)
        
        return {
            "symbol": symbol,
            "price": price,
            "previous_close": price * 0.99,
            "change": price * 0.01,
            "change_percent": 1.0,
            "volume": 100000,
            "bid": price * 0.999,
            "ask": price * 1.001,
            "bid_size": 100,
            "ask_size": 100,
            "high": price * 1.02,
            "low": price * 0.98,
            "open": price * 0.995,
            "timestamp": datetime.utcnow().isoformat(),
            "market_state": "REGULAR",
            "source": "fallback"
        }
    
    async def _get_fallback_market_status(self) -> Dict[str, Any]:
        """Get fallback market status"""
        # Check if it's a weekday and during market hours (9:15 AM - 3:30 PM IST)
        from datetime import time
        import pytz
        
        ist = pytz.timezone("Asia/Kolkata")
        now = datetime.now(ist)
        
        is_weekday = now.weekday() < 5
        market_open = time(9, 15)
        market_close = time(15, 30)
        is_market_hours = market_open <= now.time() <= market_close
        
        is_open = is_weekday and is_market_hours
        
        return {
            "is_open": is_open,
            "market_state": "REGULAR" if is_open else "CLOSED",
            "next_open": "09:15:00",
            "next_close": "15:30:00",
            "timezone": "Asia/Kolkata",
            "source": "fallback"
        }
    
    async def health_check(self) -> bool:
        """Check if market data service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.data_service_url}/health")
                return response.status_code == 200
        except Exception:
            return False

# Global market data client instance
market_data_client = MarketDataClient()