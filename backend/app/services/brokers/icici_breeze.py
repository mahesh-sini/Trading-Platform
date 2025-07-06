"""
ICICI Breeze API Integration
Official Python client for ICICI Breeze Connect API
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import aiohttp
import hashlib
import hmac
import json
import base64
from urllib.parse import urlencode

from .base_broker import (
    BaseBroker, BrokerCredentials, Quote, Position, OrderRequest, OrderResponse, 
    AccountInfo, HistoricalBar, OrderType, OrderSide, OrderStatus, AssetType,
    BrokerException, ConnectionError, AuthenticationError, OrderError, MarketDataError
)

logger = logging.getLogger(__name__)


class ICICIBreezeBroker(BaseBroker):
    """ICICI Breeze API broker implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self.base_url = "https://api.icicidirect.com/breezeapi/api"
        self.session = None
        self.session_token = None
        self.user_id = None
        
        # ICICI Breeze specific credentials
        self.api_key = credentials.api_key
        self.secret_key = credentials.secret_key
        self.session_token = credentials.additional_params.get('session_token') if credentials.additional_params else None
        
        # Rate limiting
        self.rate_limit_calls = 0
        self.rate_limit_window = datetime.now()
        self.max_calls_per_second = 10
    
    @property
    def broker_name(self) -> str:
        return "ICICI Breeze"
    
    @property
    def supported_asset_types(self) -> List[AssetType]:
        return [AssetType.STOCK, AssetType.ETF, AssetType.OPTION]
    
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT]
    
    async def connect(self) -> bool:
        """Establish connection to ICICI Breeze API"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Generate session token if not provided
            if not self.session_token:
                await self._generate_session_token()
            
            # Validate session
            await self._validate_session()
            
            self.is_connected = True
            logger.info(f"Connected to ICICI Breeze API for user: {self.user_id}")
            return True
            
        except Exception as e:
            self._handle_error(e, "Connection failed")
            if self.session:
                await self.session.close()
            raise ConnectionError(f"Failed to connect to ICICI Breeze: {str(e)}")
    
    async def disconnect(self) -> bool:
        """Disconnect from ICICI Breeze API"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            self.is_connected = False
            self.session_token = None
            logger.info("Disconnected from ICICI Breeze API")
            return True
            
        except Exception as e:
            self._handle_error(e, "Disconnection failed")
            return False
    
    async def _generate_session_token(self):
        """Generate session token"""
        try:
            # This would typically involve OAuth flow or API key authentication
            # For demo purposes, assume session token is provided
            if not self.session_token:
                raise AuthenticationError("Session token is required for ICICI Breeze")
                
        except Exception as e:
            raise AuthenticationError(f"Failed to generate session token: {str(e)}")
    
    async def _validate_session(self):
        """Validate current session"""
        try:
            headers = self._get_headers()
            
            async with self.session.get(
                f"{self.base_url}/v1/customerdetails",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.user_id = result.get('Success', {}).get('customer_id')
                else:
                    raise AuthenticationError(f"Session validation failed: {response.status}")
                    
        except Exception as e:
            raise AuthenticationError(f"Session validation failed: {str(e)}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        if not self.session_token:
            raise AuthenticationError("No session token available")
        
        return {
            'Content-Type': 'application/json',
            'X-SessionToken': self.session_token,
            'apikey': self.api_key
        }
    
    async def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        current_time = datetime.now()
        
        # Reset counter if new window
        if (current_time - self.rate_limit_window).total_seconds() >= 1:
            self.rate_limit_calls = 0
            self.rate_limit_window = current_time
        
        # Check rate limit
        if self.rate_limit_calls >= self.max_calls_per_second:
            sleep_time = 1 - (current_time - self.rate_limit_window).total_seconds()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                self.rate_limit_calls = 0
                self.rate_limit_window = datetime.now()
        
        self.rate_limit_calls += 1
    
    async def _api_call(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make API call with rate limiting and error handling"""
        await self._rate_limit_check()
        
        try:
            headers = self._get_headers()
            url = f"{self.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                async with self.session.get(url, headers=headers, params=data) as response:
                    result = await response.json()
            else:
                async with self.session.request(method, url, headers=headers, json=data) as response:
                    result = await response.json()
            
            if response.status == 200 and result.get('Status') == 'Success':
                return result
            else:
                error_msg = result.get('Error', f'API error: {response.status}')
                raise BrokerException(error_msg, self.broker_name)
                
        except Exception as e:
            if isinstance(e, BrokerException):
                raise
            raise BrokerException(f"API call failed: {str(e)}", self.broker_name)
    
    async def is_market_open(self) -> bool:
        """Check if Indian market is currently open"""
        try:
            # NSE trading hours: 09:15 - 15:30 IST (Monday to Friday)
            import pytz
            
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            # Check if weekday
            if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Check trading hours
            market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            
            return market_open <= now <= market_close
            
        except Exception:
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            # Get funds
            result = await self._api_call('GET', '/v1/funds')
            funds_data = result['Success']
            
            return AccountInfo(
                account_id=self.user_id,
                buying_power=Decimal(str(funds_data.get('available_margin', 0))),
                cash=Decimal(str(funds_data.get('cash', 0))),
                equity=Decimal(str(funds_data.get('net_amount', 0))),
                day_trading_buying_power=Decimal(str(funds_data.get('intraday_margin', 0))),
                maintenance_margin=Decimal(str(funds_data.get('used_margin', 0))),
                currency="INR"
            )
            
        except Exception as e:
            raise BrokerException(f"Failed to get account info: {str(e)}", self.broker_name)
    
    async def get_positions(self) -> List[Position]:
        """Get all account positions"""
        try:
            result = await self._api_call('GET', '/v1/portfolioholdings')
            positions = []
            
            for pos_data in result['Success']:
                if pos_data['quantity'] != 0:  # Only non-zero positions
                    positions.append(Position(
                        symbol=pos_data['stock_code'],
                        quantity=Decimal(str(pos_data['quantity'])),
                        average_price=Decimal(str(pos_data['average_price'])),
                        current_price=Decimal(str(pos_data['current_price'])),
                        market_value=Decimal(str(pos_data['quantity'] * pos_data['current_price'])),
                        unrealized_pnl=Decimal(str(pos_data['pnl'])),
                        asset_type=AssetType.STOCK,
                        side="long" if pos_data['quantity'] > 0 else "short"
                    ))
            
            return positions
            
        except Exception as e:
            raise BrokerException(f"Failed to get positions: {str(e)}", self.broker_name)
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for specific symbol"""
        positions = await self.get_positions()
        return next((pos for pos in positions if pos.symbol == symbol), None)
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote for symbol"""
        try:
            data = {
                'stock_code': symbol,
                'exchange_code': 'NSE'
            }
            
            result = await self._api_call('GET', '/v1/quotes', data)
            quote_data = result['Success']
            
            return Quote(
                symbol=symbol,
                bid=Decimal(str(quote_data.get('bid', 0))),
                ask=Decimal(str(quote_data.get('ask', 0))),
                last=Decimal(str(quote_data['ltp'])),
                volume=quote_data.get('volume', 0),
                timestamp=datetime.now(),
                high=Decimal(str(quote_data.get('high', 0))),
                low=Decimal(str(quote_data.get('low', 0))),
                open=Decimal(str(quote_data.get('open', 0))),
                close=Decimal(str(quote_data.get('close', 0)))
            )
            
        except Exception as e:
            raise MarketDataError(f"Failed to get quote for {symbol}: {str(e)}", self.broker_name)
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        
        # ICICI Breeze may require individual calls for each symbol
        for symbol in symbols:
            try:
                quotes[symbol] = await self.get_quote(symbol)
            except Exception as e:
                logger.warning(f"Failed to get quote for {symbol}: {str(e)}")
        
        return quotes
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[HistoricalBar]:
        """Get historical price data"""
        try:
            # Set default dates if not provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Map period to ICICI Breeze format
            interval_map = {
                '1m': '1minute',
                '5m': '5minute',
                '15m': '15minute',
                '1h': '1hour',
                '1d': '1day'
            }
            
            interval = interval_map.get(period, '1day')
            
            data = {
                'stock_code': symbol,
                'exchange_code': 'NSE',
                'interval': interval,
                'from_date': start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                'to_date': end_date.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            }
            
            result = await self._api_call('GET', '/v1/historicalcharts', data)
            
            bars = []
            for candle in result['Success']:
                bars.append(HistoricalBar(
                    timestamp=datetime.fromisoformat(candle['datetime']),
                    open=Decimal(str(candle['open'])),
                    high=Decimal(str(candle['high'])),
                    low=Decimal(str(candle['low'])),
                    close=Decimal(str(candle['close'])),
                    volume=candle['volume']
                ))
            
            return bars
            
        except Exception as e:
            raise MarketDataError(f"Failed to get historical data: {str(e)}", self.broker_name)
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place a trading order"""
        try:
            self._validate_order_request(order)
            
            # Map order types to ICICI Breeze format
            order_type_map = {
                OrderType.MARKET: 'market',
                OrderType.LIMIT: 'limit',
                OrderType.STOP: 'stop_loss',
                OrderType.STOP_LIMIT: 'stop_loss_limit'
            }
            
            side_map = {
                OrderSide.BUY: 'buy',
                OrderSide.SELL: 'sell'
            }
            
            order_data = {
                'stock_code': order.symbol,
                'exchange_code': 'NSE',
                'action': side_map[order.side],
                'quantity': str(order.quantity),
                'order_type': order_type_map[order.order_type],
                'product_type': 'delivery',
                'validity': 'day'
            }
            
            if order.price:
                order_data['price'] = str(order.price)
            
            if order.stop_price:
                order_data['stoploss'] = str(order.stop_price)
            
            result = await self._api_call('POST', '/v1/order', order_data)
            
            return OrderResponse(
                order_id=result['Success']['order_id'],
                status=OrderStatus.SUBMITTED,
                symbol=order.symbol,
                quantity=order.quantity,
                filled_quantity=0,
                average_fill_price=None,
                timestamp=datetime.now(),
                commission=None
            )
            
        except Exception as e:
            raise OrderError(f"Failed to place order: {str(e)}", self.broker_name)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            data = {'order_id': order_id}
            await self._api_call('DELETE', '/v1/order', data)
            return True
            
        except Exception as e:
            raise OrderError(f"Failed to cancel order: {str(e)}", self.broker_name)
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order"""
        try:
            data = {'order_id': order_id}
            result = await self._api_call('GET', '/v1/order', data)
            order_data = result['Success']
            
            status_map = {
                'pending': OrderStatus.SUBMITTED,
                'complete': OrderStatus.FILLED,
                'cancelled': OrderStatus.CANCELLED,
                'rejected': OrderStatus.REJECTED
            }
            
            return OrderResponse(
                order_id=order_data['order_id'],
                status=status_map.get(order_data['status'], OrderStatus.PENDING),
                symbol=order_data['stock_code'],
                quantity=int(order_data['quantity']),
                filled_quantity=int(order_data.get('filled_quantity', 0)),
                average_fill_price=Decimal(str(order_data['average_price'])) if order_data.get('average_price') else None,
                timestamp=datetime.fromisoformat(order_data['order_datetime']),
                commission=None
            )
            
        except Exception as e:
            raise OrderError(f"Failed to get order status: {str(e)}", self.broker_name)
    
    async def get_orders(
        self, 
        status: Optional[OrderStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[OrderResponse]:
        """Get order history"""
        try:
            result = await self._api_call('GET', '/v1/orderbook')
            orders = []
            
            status_map = {
                'pending': OrderStatus.SUBMITTED,
                'complete': OrderStatus.FILLED,
                'cancelled': OrderStatus.CANCELLED,
                'rejected': OrderStatus.REJECTED
            }
            
            for order_data in result['Success']:
                order_status = status_map.get(order_data['status'], OrderStatus.PENDING)
                
                # Filter by status if specified
                if status and order_status != status:
                    continue
                
                # Filter by date range if specified
                order_time = datetime.fromisoformat(order_data['order_datetime'])
                if start_date and order_time < start_date:
                    continue
                if end_date and order_time > end_date:
                    continue
                
                orders.append(OrderResponse(
                    order_id=order_data['order_id'],
                    status=order_status,
                    symbol=order_data['stock_code'],
                    quantity=int(order_data['quantity']),
                    filled_quantity=int(order_data.get('filled_quantity', 0)),
                    average_fill_price=Decimal(str(order_data['average_price'])) if order_data.get('average_price') else None,
                    timestamp=order_time,
                    commission=None
                ))
            
            return orders
            
        except Exception as e:
            raise OrderError(f"Failed to get orders: {str(e)}", self.broker_name)
    
    async def get_options_chain(
        self, 
        underlying_symbol: str,
        expiration_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get options chain"""
        try:
            data = {
                'stock_code': underlying_symbol,
                'exchange_code': 'NSE'
            }
            
            if expiration_date:
                data['expiry_date'] = expiration_date.strftime('%Y-%m-%d')
            
            result = await self._api_call('GET', '/v1/optionchain', data)
            return result['Success']
            
        except Exception as e:
            raise MarketDataError(f"Failed to get options chain: {str(e)}", self.broker_name)
    
    def _validate_symbol(self, symbol: str) -> str:
        """Validate and normalize symbol format for Indian markets"""
        symbol = symbol.upper().strip()
        
        # Remove any exchange suffix for ICICI Breeze
        if symbol.endswith('.NS'):
            symbol = symbol[:-3]
        elif symbol.endswith('.BSE'):
            symbol = symbol[:-4]
        
        return symbol