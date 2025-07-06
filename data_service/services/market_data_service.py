import asyncio
import logging
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import redis
import json
import websockets
import aiohttp
from services.data_ingestion import data_ingestion_service, DataSource

logger = logging.getLogger(__name__)

class MarketStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"

@dataclass
class QuoteData:
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    change: float
    change_percent: float
    timestamp: datetime
    market_status: MarketStatus

@dataclass
class SymbolInfo:
    symbol: str
    company_name: str
    exchange: str
    sector: str
    industry: str
    market_cap: float
    shares_outstanding: float

class MarketDataService:
    def __init__(self):
        self.redis_client = None
        self.quote_cache = {}
        self.subscriptions = set()
        self.websocket_connections = []
        self.is_running = False
        
    async def initialize(self):
        """Initialize the market data service"""
        logger.info("Initializing Market Data Service")
        
        # Initialize Redis connection for caching
        try:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis connection established for market data caching")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {str(e)}")
        
        self.is_running = True
        
        # Start background tasks
        asyncio.create_task(self._quote_updater())
        asyncio.create_task(self._market_status_monitor())
        
    async def shutdown(self):
        """Shutdown the market data service"""
        self.is_running = False
        if self.redis_client:
            self.redis_client.close()
        logger.info("Market Data Service shutdown complete")
    
    async def get_quote(self, symbol: str, force_refresh: bool = False) -> Optional[QuoteData]:
        """Get current quote for a symbol"""
        try:
            # Check cache first unless force refresh
            if not force_refresh and self.redis_client:
                cached_quote = self.redis_client.get(f"quote:{symbol}")
                if cached_quote:
                    quote_data = json.loads(cached_quote)
                    return QuoteData(
                        symbol=quote_data['symbol'],
                        price=quote_data['price'],
                        bid=quote_data['bid'],
                        ask=quote_data['ask'],
                        volume=quote_data['volume'],
                        change=quote_data['change'],
                        change_percent=quote_data['change_percent'],
                        timestamp=datetime.fromisoformat(quote_data['timestamp']),
                        market_status=MarketStatus(quote_data['market_status'])
                    )
            
            # Get fresh data from data ingestion service
            market_data_point = await data_ingestion_service.get_real_time_data(symbol)
            
            if not market_data_point:
                return None
            
            # Get previous close from historical data
            try:
                # Get yesterday's data for comparison
                historical_data = await data_ingestion_service.get_historical_data(symbol, "2d")
                if len(historical_data) >= 2:
                    previous_close = historical_data.iloc[-2]['close']
                else:
                    # Fallback: use current price as baseline
                    previous_close = market_data_point.close_price
                
                change = market_data_point.close_price - previous_close
                change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
            except Exception as e:
                logger.warning(f"Failed to get previous close for {symbol}: {e}")
                previous_close = market_data_point.close_price
                change = 0
                change_percent = 0
            
            # Determine market status
            market_status = await self._get_market_status(symbol)
            
            quote = QuoteData(
                symbol=symbol,
                price=market_data_point.close_price,
                bid=market_data_point.bid_price if hasattr(market_data_point, 'bid_price') else market_data_point.close_price * 0.999,
                ask=market_data_point.ask_price if hasattr(market_data_point, 'ask_price') else market_data_point.close_price * 1.001,
                volume=market_data_point.volume,
                change=change,
                change_percent=change_percent,
                timestamp=market_data_point.timestamp,
                market_status=market_status
            )
            
            # Cache the quote
            if self.redis_client:
                quote_json = {
                    'symbol': quote.symbol,
                    'price': quote.price,
                    'bid': quote.bid,
                    'ask': quote.ask,
                    'volume': quote.volume,
                    'change': quote.change,
                    'change_percent': quote.change_percent,
                    'timestamp': quote.timestamp.isoformat(),
                    'market_status': quote.market_status.value
                }
                self.redis_client.setex(f"quote:{symbol}", 60, json.dumps(quote_json))
            
            return quote
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {str(e)}")
            return None
    
    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """Get quotes for multiple symbols"""
        quotes = {}
        
        # Process in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            
            # Get quotes concurrently for the batch
            tasks = [self.get_quote(symbol) for symbol in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for symbol, result in zip(batch, results):
                if isinstance(result, QuoteData):
                    quotes[symbol] = result
                else:
                    logger.warning(f"Failed to get quote for {symbol}: {result}")
        
        return quotes
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """Get historical market data"""
        try:
            # Check cache first
            cache_key = f"historical:{symbol}:{period}:{interval}"
            if self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data_dict = json.loads(cached_data)
                    return pd.DataFrame(data_dict)
            
            # Get fresh data
            data = await data_ingestion_service.get_historical_data(symbol, period)
            
            if not data.empty:
                # Cache for 1 hour
                if self.redis_client:
                    self.redis_client.setex(cache_key, 3600, data.to_json())
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    async def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get detailed symbol information"""
        try:
            # Check cache first
            cache_key = f"symbol_info:{symbol}"
            if self.redis_client:
                cached_info = self.redis_client.get(cache_key)
                if cached_info:
                    info_data = json.loads(cached_info)
                    return SymbolInfo(**info_data)
            
            # Get symbol info from Yahoo Finance (placeholder implementation)
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return None
            
            symbol_info = SymbolInfo(
                symbol=symbol,
                company_name=info.get('longName', ''),
                exchange=info.get('exchange', ''),
                sector=info.get('sector', ''),
                industry=info.get('industry', ''),
                market_cap=info.get('marketCap', 0),
                shares_outstanding=info.get('sharesOutstanding', 0)
            )
            
            # Cache for 24 hours
            if self.redis_client:
                info_dict = {
                    'symbol': symbol_info.symbol,
                    'company_name': symbol_info.company_name,
                    'exchange': symbol_info.exchange,
                    'sector': symbol_info.sector,
                    'industry': symbol_info.industry,
                    'market_cap': symbol_info.market_cap,
                    'shares_outstanding': symbol_info.shares_outstanding
                }
                self.redis_client.setex(cache_key, 86400, json.dumps(info_dict))
            
            return symbol_info
            
        except Exception as e:
            logger.error(f"Failed to get symbol info for {symbol}: {str(e)}")
            return None
    
    async def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """Search for symbols by name or ticker"""
        try:
            # Use real symbol search from data providers
            results = await data_ingestion_service.search_symbols(query, limit)
            return results
            
        except Exception as e:
            logger.error(f"Symbol search failed for query '{query}': {str(e)}")
            return []
    
    async def subscribe_to_symbol(self, symbol: str):
        """Subscribe to real-time updates for a symbol"""
        self.subscriptions.add(symbol)
        logger.info(f"Subscribed to {symbol}")
    
    async def unsubscribe_from_symbol(self, symbol: str):
        """Unsubscribe from real-time updates for a symbol"""
        self.subscriptions.discard(symbol)
        logger.info(f"Unsubscribed from {symbol}")
    
    async def get_market_hours(self, exchange: str = "NYSE") -> Dict[str, Any]:
        """Get market hours for an exchange"""
        # Get real market hours from data provider
        try:
            market_hours = await data_ingestion_service.get_market_hours(exchange)
            return market_hours
        except Exception as e:
            logger.error(f"Failed to get market hours for {exchange}: {e}")
            # Fallback to default NYSE hours
            return {
                "exchange": exchange,
                "is_open": await self._is_market_open(),
                "market_open": "09:30:00",
                "market_close": "16:00:00",
                "timezone": "America/New_York",
                "pre_market_open": "04:00:00",
                "after_hours_close": "20:00:00"
            }
    
    async def _get_market_status(self, symbol: str = "SPY") -> MarketStatus:
        """Determine current market status"""
        # Get real market status from data provider
        try:
            is_open = await data_ingestion_service.is_market_open()
            if is_open:
                return MarketStatus.OPEN
            
            # Check if it's pre-market or after hours based on time
            from datetime import datetime
            import pytz
            
            et = pytz.timezone('America/New_York')
            current_time = datetime.now(et)
            current_hour = current_time.hour
            
            if 4 <= current_hour < 9:
                return MarketStatus.PRE_MARKET
            elif 16 <= current_hour < 20:
                return MarketStatus.AFTER_HOURS
            else:
                return MarketStatus.CLOSED
                
        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            # Fallback to simple time-based logic
            current_hour = datetime.now().hour
            
            if 9 <= current_hour < 16:
                return MarketStatus.OPEN
            elif 4 <= current_hour < 9:
                return MarketStatus.PRE_MARKET
            elif 16 <= current_hour < 20:
                return MarketStatus.AFTER_HOURS
            else:
                return MarketStatus.CLOSED
    
    async def _quote_updater(self):
        """Background task to update quotes for subscribed symbols"""
        while self.is_running:
            try:
                if self.subscriptions:
                    logger.debug(f"Updating quotes for {len(self.subscriptions)} subscribed symbols")
                    
                    # Update quotes for subscribed symbols
                    for symbol in self.subscriptions.copy():
                        try:
                            quote = await self.get_quote(symbol, force_refresh=True)
                            if quote:
                                # Broadcast to WebSocket connections if any
                                await self._broadcast_quote_update(quote)
                        except Exception as e:
                            logger.error(f"Error updating quote for {symbol}: {str(e)}")
                
                # Wait 30 seconds before next update
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Quote updater error: {str(e)}")
                await asyncio.sleep(30)
    
    async def _market_status_monitor(self):
        """Background task to monitor market status"""
        while self.is_running:
            try:
                # Check market status every 5 minutes
                status = await self._get_market_status()
                
                # Cache market status
                if self.redis_client:
                    self.redis_client.setex("market_status", 300, status.value)
                
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Market status monitor error: {str(e)}")
                await asyncio.sleep(300)
    
    async def _broadcast_quote_update(self, quote: QuoteData):
        """Broadcast quote update to WebSocket connections"""
        if not self.websocket_connections:
            return
        
        message = {
            "type": "quote_update",
            "symbol": quote.symbol,
            "price": quote.price,
            "change": quote.change,
            "change_percent": quote.change_percent,
            "timestamp": quote.timestamp.isoformat()
        }
        
        # Remove closed connections
        active_connections = []
        for ws in self.websocket_connections:
            try:
                await ws.send(json.dumps(message))
                active_connections.append(ws)
            except Exception:
                # Connection closed
                pass
        
        self.websocket_connections = active_connections
    
    async def add_websocket_connection(self, websocket):
        """Add a WebSocket connection for real-time updates"""
        self.websocket_connections.append(websocket)
        logger.info("WebSocket connection added")
    
    async def remove_websocket_connection(self, websocket):
        """Remove a WebSocket connection"""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
            logger.info("WebSocket connection removed")
    
    async def _is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            return await data_ingestion_service.is_market_open()
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            # Fallback to simple time check
            current_hour = datetime.now().hour
            return 9 <= current_hour < 16

# Singleton instance
market_data_service = MarketDataService()