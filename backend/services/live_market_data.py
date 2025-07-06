"""
Live Market Data Service - Production Implementation
Integrates with real Indian market data providers
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import json
from decimal import Decimal
import os

from monitoring.metrics import trading_metrics
from monitoring.logging_config import market_data_logger
from services.indian_broker_apis import IndianBrokerAPIService

# Note: These imports are commented out as they may not exist yet
# from models.market_data import MarketData, Quote, HistoricalBar
# from services.database import get_db
# from websocket.connection_manager import ConnectionManager

# Mock ConnectionManager for now
class ConnectionManager:
    async def broadcast_to_symbol(self, symbol: str, data: dict):
        # TODO: Implement WebSocket broadcasting
        pass

logger = logging.getLogger(__name__)

class LiveMarketDataService:
    """Production market data service with multiple provider support"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket_connections: Dict[str, Any] = {}
        self.subscribed_symbols: set = set()
        self.connection_manager = ConnectionManager()
        
        # Initialize Indian broker API service
        self.indian_brokers = IndianBrokerAPIService()
        
        # Market data providers configuration
        self.providers = {
            'nse': {
                'base_url': 'https://www.nseindia.com/api',
                'enabled': True,
                'rate_limit': 100  # requests per minute
            },
            'yahoo_finance': {
                'base_url': 'https://query1.finance.yahoo.com/v8/finance',
                'enabled': True,
                'rate_limit': 200
            },
            'alpha_vantage': {
                'api_key': os.getenv('ALPHA_VANTAGE_API_KEY'),
                'base_url': 'https://www.alphavantage.co/query',
                'enabled': bool(os.getenv('ALPHA_VANTAGE_API_KEY')),
                'rate_limit': 5  # requests per minute (free tier)
            },
            'polygon': {
                'api_key': os.getenv('POLYGON_API_KEY'),
                'base_url': 'https://api.polygon.io',
                'enabled': bool(os.getenv('POLYGON_API_KEY')),
                'rate_limit': 100
            }
        }
        
        # Rate limiting tracking
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self):
        """Initialize the market data service"""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'AI-Trading-Platform/1.0'
                }
            )
            
            # Initialize rate limiting
            for provider in self.providers:
                self.rate_limits[provider] = {
                    'requests': [],
                    'last_reset': datetime.now()
                }
            
            logger.info("Live market data service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize market data service: {e}")
            raise
    
    async def close(self):
        """Clean up resources"""
        try:
            if self.session:
                await self.session.close()
            
            # Close WebSocket connections
            for ws in self.websocket_connections.values():
                if not ws.closed:
                    await ws.close()
            
            # Close Indian broker API service
            await self.indian_brokers.close()
                    
            logger.info("Market data service closed")
            
        except Exception as e:
            logger.error(f"Error closing market data service: {e}")
    
    async def get_live_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Get real-time quote for a symbol"""
        start_time = time.time()
        
        try:
            market_data_logger.info(f"Fetching live quote for {symbol} on {exchange}")
            
            # Try Indian broker APIs first for Indian stocks (highest priority)
            if exchange == "NSE" and self.indian_brokers.get_available_providers():
                quote = await self.indian_brokers.get_best_quote(symbol)
                if quote:
                    latency = time.time() - start_time
                    trading_metrics.record_market_data_update({
                        'symbol': symbol,
                        'data_type': 'quote',
                        'provider': quote.get('provider', 'indian_broker'),
                        'latency': latency,
                        'age': 0
                    })
                    market_data_logger.market_data_update({
                        'symbol': symbol,
                        'data_type': 'quote',
                        'latency': latency,
                        'age': 0
                    })
                    return quote
            
            # Fallback to NSE direct API
            if exchange == "NSE":
                quote = await self._get_nse_quote(symbol)
                if quote:
                    latency = time.time() - start_time
                    trading_metrics.record_market_data_update({
                        'symbol': symbol,
                        'data_type': 'quote',
                        'provider': 'nse',
                        'latency': latency,
                        'age': 0
                    })
                    market_data_logger.market_data_update({
                        'symbol': symbol,
                        'data_type': 'quote',
                        'latency': latency,
                        'age': 0
                    })
                    return quote
            
            # Fallback to Yahoo Finance
            quote = await self._get_yahoo_quote(f"{symbol}.NS")
            if quote:
                latency = time.time() - start_time
                trading_metrics.record_market_data_update({
                    'symbol': symbol,
                    'data_type': 'quote',
                    'provider': 'yahoo_finance',
                    'latency': latency,
                    'age': 0
                })
                market_data_logger.market_data_update({
                    'symbol': symbol,
                    'data_type': 'quote',
                    'latency': latency,
                    'age': 0
                })
                return quote
            
            # Fallback to Alpha Vantage
            if self.providers['alpha_vantage']['enabled']:
                quote = await self._get_alpha_vantage_quote(symbol)
                if quote:
                    latency = time.time() - start_time
                    trading_metrics.record_market_data_update({
                        'symbol': symbol,
                        'data_type': 'quote',
                        'provider': 'alpha_vantage',
                        'latency': latency,
                        'age': 0
                    })
                    market_data_logger.market_data_update({
                        'symbol': symbol,
                        'data_type': 'quote',
                        'latency': latency,
                        'age': 0
                    })
                    return quote
            
            logger.warning(f"No quote data found for {symbol}")
            trading_metrics.record_provider_error({
                'provider': 'all',
                'error_type': 'no_data'
            })
            return None
            
        except Exception as e:
            logger.error(f"Error getting live quote for {symbol}: {e}")
            return None
    
    async def _get_nse_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from NSE India"""
        try:
            if not await self._check_rate_limit('nse'):
                trading_metrics.record_provider_error({
                    'provider': 'nse',
                    'error_type': 'rate_limit_exceeded'
                })
                return None
            
            url = f"{self.providers['nse']['base_url']}/quote-equity"
            params = {'symbol': symbol}
            
            async with self.session.get(url, params=params) as response:
                trading_metrics.record_provider_api_call({
                    'provider': 'nse',
                    'endpoint': 'quote-equity',
                    'status': 'success' if response.status == 200 else 'error'
                })
                
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_nse_quote(data)
                else:
                    logger.warning(f"NSE API returned status {response.status} for {symbol}")
                    trading_metrics.record_provider_error({
                        'provider': 'nse',
                        'error_type': f'http_{response.status}'
                    })
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching NSE quote for {symbol}: {e}")
            trading_metrics.record_provider_error({
                'provider': 'nse',
                'error_type': 'api_exception'
            })
            return None
    
    async def _get_yahoo_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from Yahoo Finance"""
        try:
            if not await self._check_rate_limit('yahoo_finance'):
                trading_metrics.record_provider_error({
                    'provider': 'yahoo_finance',
                    'error_type': 'rate_limit_exceeded'
                })
                return None
            
            url = f"{self.providers['yahoo_finance']['base_url']}/chart/{symbol}"
            params = {
                'interval': '1m',
                'range': '1d',
                'includePrePost': 'false'
            }
            
            async with self.session.get(url, params=params) as response:
                trading_metrics.record_provider_api_call({
                    'provider': 'yahoo_finance',
                    'endpoint': 'chart',
                    'status': 'success' if response.status == 200 else 'error'
                })
                
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_yahoo_quote(data, symbol)
                else:
                    logger.warning(f"Yahoo Finance API returned status {response.status} for {symbol}")
                    trading_metrics.record_provider_error({
                        'provider': 'yahoo_finance',
                        'error_type': f'http_{response.status}'
                    })
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Yahoo quote for {symbol}: {e}")
            trading_metrics.record_provider_error({
                'provider': 'yahoo_finance',
                'error_type': 'api_exception'
            })
            return None
    
    async def _get_alpha_vantage_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote from Alpha Vantage"""
        try:
            if not await self._check_rate_limit('alpha_vantage'):
                return None
            
            url = self.providers['alpha_vantage']['base_url']
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': f"{symbol}.BSE",  # Try BSE format
                'apikey': self.providers['alpha_vantage']['api_key']
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_alpha_vantage_quote(data, symbol)
                else:
                    logger.warning(f"Alpha Vantage API returned status {response.status} for {symbol}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage quote for {symbol}: {e}")
            return None
    
    def _normalize_nse_quote(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize NSE quote data"""
        try:
            price_info = data.get('priceInfo', {})
            return {
                'symbol': data.get('info', {}).get('symbol'),
                'price': float(price_info.get('lastPrice', 0)),
                'change': float(price_info.get('change', 0)),
                'change_percent': float(price_info.get('pChange', 0)),
                'volume': int(data.get('securityWiseDP', {}).get('quantityTraded', 0)),
                'high': float(price_info.get('intraDayHighLow', {}).get('max', 0)),
                'low': float(price_info.get('intraDayHighLow', {}).get('min', 0)),
                'open': float(price_info.get('open', 0)),
                'previous_close': float(price_info.get('close', 0)),
                'bid': float(price_info.get('lastPrice', 0)) - 0.05,  # Approximate
                'ask': float(price_info.get('lastPrice', 0)) + 0.05,  # Approximate
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'exchange': 'NSE',
                'currency': 'INR'
            }
        except Exception as e:
            logger.error(f"Error normalizing NSE quote: {e}")
            return {}
    
    def _normalize_yahoo_quote(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Normalize Yahoo Finance quote data"""
        try:
            chart = data.get('chart', {})
            result = chart.get('result', [{}])[0]
            meta = result.get('meta', {})
            
            return {
                'symbol': symbol.replace('.NS', '').replace('.BSE', ''),
                'price': float(meta.get('regularMarketPrice', 0)),
                'change': float(meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0)),
                'change_percent': ((float(meta.get('regularMarketPrice', 0)) - float(meta.get('previousClose', 0))) / float(meta.get('previousClose', 1))) * 100,
                'volume': int(meta.get('regularMarketVolume', 0)),
                'high': float(meta.get('regularMarketDayHigh', 0)),
                'low': float(meta.get('regularMarketDayLow', 0)),
                'open': float(meta.get('regularMarketOpen', 0)),
                'previous_close': float(meta.get('previousClose', 0)),
                'bid': float(meta.get('bid', 0)),
                'ask': float(meta.get('ask', 0)),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'exchange': 'NSE' if '.NS' in symbol else 'BSE',
                'currency': meta.get('currency', 'INR')
            }
        except Exception as e:
            logger.error(f"Error normalizing Yahoo quote: {e}")
            return {}
    
    def _normalize_alpha_vantage_quote(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Normalize Alpha Vantage quote data"""
        try:
            quote = data.get('Global Quote', {})
            price = float(quote.get('05. price', 0))
            prev_close = float(quote.get('08. previous close', 0))
            
            return {
                'symbol': symbol,
                'price': price,
                'change': price - prev_close,
                'change_percent': float(quote.get('10. change percent', '0%').replace('%', '')),
                'volume': int(quote.get('06. volume', 0)),
                'high': float(quote.get('03. high', 0)),
                'low': float(quote.get('04. low', 0)),
                'open': float(quote.get('02. open', 0)),
                'previous_close': prev_close,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'exchange': 'BSE',
                'currency': 'INR'
            }
        except Exception as e:
            logger.error(f"Error normalizing Alpha Vantage quote: {e}")
            return {}
    
    async def _check_rate_limit(self, provider: str) -> bool:
        """Check if provider is within rate limits"""
        try:
            now = datetime.now()
            provider_limits = self.rate_limits[provider]
            
            # Remove requests older than 1 minute
            provider_limits['requests'] = [
                req_time for req_time in provider_limits['requests']
                if (now - req_time).total_seconds() < 60
            ]
            
            # Check if within limit
            if len(provider_limits['requests']) >= self.providers[provider]['rate_limit']:
                logger.warning(f"Rate limit exceeded for {provider}")
                return False
            
            # Add current request
            provider_limits['requests'].append(now)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit for {provider}: {e}")
            return False
    
    async def get_historical_data(self, symbol: str, period: str = "1d", 
                                 start_date: Optional[datetime] = None,
                                 end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get historical market data"""
        try:
            # Try Yahoo Finance for historical data
            yahoo_symbol = f"{symbol}.NS"
            
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            url = f"{self.providers['yahoo_finance']['base_url']}/chart/{yahoo_symbol}"
            params = {
                'period1': int(start_date.timestamp()),
                'period2': int(end_date.timestamp()),
                'interval': period,
                'includePrePost': 'false'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_historical_data(data)
                else:
                    logger.warning(f"Failed to get historical data for {symbol}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    def _normalize_historical_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Normalize historical data from Yahoo Finance"""
        try:
            chart = data.get('chart', {})
            result = chart.get('result', [{}])[0]
            
            timestamps = result.get('timestamp', [])
            ohlc = result.get('indicators', {}).get('quote', [{}])[0]
            
            historical_data = []
            for i, timestamp in enumerate(timestamps):
                historical_data.append({
                    'timestamp': datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
                    'open': float(ohlc.get('open', [])[i] or 0),
                    'high': float(ohlc.get('high', [])[i] or 0),
                    'low': float(ohlc.get('low', [])[i] or 0),
                    'close': float(ohlc.get('close', [])[i] or 0),
                    'volume': int(ohlc.get('volume', [])[i] or 0)
                })
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error normalizing historical data: {e}")
            return []
    
    async def subscribe_to_real_time(self, symbols: List[str]):
        """Subscribe to real-time updates for symbols"""
        try:
            for symbol in symbols:
                if symbol not in self.subscribed_symbols:
                    self.subscribed_symbols.add(symbol)
                    # Start background task for real-time updates
                    asyncio.create_task(self._real_time_update_loop(symbol))
            
            logger.info(f"Subscribed to real-time updates for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error subscribing to real-time updates: {e}")
    
    async def _real_time_update_loop(self, symbol: str):
        """Background loop for real-time updates"""
        try:
            while symbol in self.subscribed_symbols:
                quote = await self.get_live_quote(symbol)
                if quote:
                    # Broadcast to WebSocket clients
                    await self.connection_manager.broadcast_to_symbol(symbol, {
                        'type': 'market_data_update',
                        'symbol': symbol,
                        'data': quote,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                
                # Wait before next update (adjust based on requirements)
                await asyncio.sleep(2)  # 2 second updates
                
        except Exception as e:
            logger.error(f"Error in real-time update loop for {symbol}: {e}")
        finally:
            self.subscribed_symbols.discard(symbol)

# Global instance
live_market_data_service = LiveMarketDataService()