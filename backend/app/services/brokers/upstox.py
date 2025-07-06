"""
Upstox API Integration
Official Python client for Upstox Connect API
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import aiohttp
import json
from urllib.parse import urlencode

from .base_broker import (
    BaseBroker, BrokerCredentials, Quote, Position, OrderRequest, OrderResponse, 
    AccountInfo, HistoricalBar, OrderType, OrderSide, OrderStatus, AssetType,
    BrokerException, ConnectionError, AuthenticationError, OrderError, MarketDataError
)

logger = logging.getLogger(__name__)


class UpstoxBroker(BaseBroker):
    """Upstox API broker implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self.base_url = "https://api.upstox.com/v2"
        self.session = None
        self.access_token = None
        self.user_id = None
        
        # Upstox specific credentials
        self.api_key = credentials.api_key
        self.api_secret = credentials.secret_key
        self.redirect_uri = credentials.additional_params.get('redirect_uri') if credentials.additional_params else None
        self.authorization_code = credentials.additional_params.get('authorization_code') if credentials.additional_params else None
        
        # Rate limiting
        self.rate_limit_calls = 0
        self.rate_limit_window = datetime.now()
        self.max_calls_per_second = 25  # Upstox allows 25 calls per second
    
    @property
    def broker_name(self) -> str:
        return "Upstox"
    
    @property
    def supported_asset_types(self) -> List[AssetType]:
        return [AssetType.STOCK, AssetType.ETF, AssetType.OPTION]
    
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP_LIMIT]
    
    async def connect(self) -> bool:
        """Establish connection to Upstox API"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Generate access token if authorization code is provided
            if self.authorization_code:
                await self._generate_access_token()
            
            # Validate session
            await self._validate_session()
            
            self.is_connected = True
            logger.info(f"Connected to Upstox API for user: {self.user_id}")
            return True
            
        except Exception as e:
            self._handle_error(e, "Connection failed")
            if self.session:
                await self.session.close()
            raise ConnectionError(f"Failed to connect to Upstox: {str(e)}")
    
    async def disconnect(self) -> bool:
        """Disconnect from Upstox API"""
        try:
            if self.session:
                await self.session.close()
                self.session = None
            
            self.is_connected = False
            self.access_token = None
            logger.info("Disconnected from Upstox API")
            return True
            
        except Exception as e:
            self._handle_error(e, "Disconnection failed")
            return False
    
    async def _generate_access_token(self):
        """Generate access token using authorization code"""
        try:
            token_url = "https://api.upstox.com/v2/login/authorization/token"
            
            data = {
                'code': self.authorization_code,
                'client_id': self.api_key,
                'client_secret': self.api_secret,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            async with self.session.post(token_url, data=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    self.access_token = result['access_token']
                else:
                    raise AuthenticationError(f"Token generation failed: {response.status}")
                    
        except Exception as e:
            raise AuthenticationError(f"Failed to generate access token: {str(e)}")
    
    async def _validate_session(self):
        """Validate current session"""
        try:
            headers = self._get_headers()
            
            async with self.session.get(
                f"{self.base_url}/user/profile",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.user_id = result['data']['user_id']
                else:
                    raise AuthenticationError(f"Session validation failed: {response.status}")
                    
        except Exception as e:
            raise AuthenticationError(f"Session validation failed: {str(e)}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        if not self.access_token:
            raise AuthenticationError("No access token available")
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
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
            
            if response.status == 200 and result.get('status') == 'success':
                return result
            else:
                error_msg = result.get('message', f'API error: {response.status}')
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
            # Get user funds
            result = await self._api_call('GET', '/user/get-funds-and-margin')
            funds_data = result['data']['equity']
            
            return AccountInfo(
                account_id=self.user_id,
                buying_power=Decimal(str(funds_data.get('available_margin', 0))),
                cash=Decimal(str(funds_data.get('payin_amount', 0))),
                equity=Decimal(str(funds_data.get('total_balance', 0))),
                day_trading_buying_power=Decimal(str(funds_data.get('intraday_payin', 0))),
                maintenance_margin=Decimal(str(funds_data.get('used_margin', 0))),
                currency="INR"
            )
            
        except Exception as e:
            raise BrokerException(f"Failed to get account info: {str(e)}", self.broker_name)
    
    async def get_positions(self) -> List[Position]:
        """Get all account positions"""
        try:
            result = await self._api_call('GET', '/portfolio/long-term-positions')
            positions = []
            
            for pos_data in result['data']:
                if pos_data['quantity'] != 0:  # Only non-zero positions
                    positions.append(Position(
                        symbol=pos_data['instrument_token'],
                        quantity=Decimal(str(pos_data['quantity'])),
                        average_price=Decimal(str(pos_data['average_price'])),
                        current_price=Decimal(str(pos_data['last_price'])),
                        market_value=Decimal(str(pos_data['quantity'] * pos_data['last_price'])),
                        unrealized_pnl=Decimal(str(pos_data['unrealised'])),
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
            # Convert symbol to instrument key format
            instrument_key = await self._get_instrument_key(symbol)
            
            result = await self._api_call('GET', f'/market-quote/quotes?instrument_key={instrument_key}')
            quote_data = result['data'][instrument_key]
            
            return Quote(
                symbol=symbol,
                bid=Decimal(str(quote_data['depth']['buy'][0]['price'])) if quote_data['depth']['buy'] else None,
                ask=Decimal(str(quote_data['depth']['sell'][0]['price'])) if quote_data['depth']['sell'] else None,
                last=Decimal(str(quote_data['last_price'])),
                volume=quote_data['volume'],
                timestamp=datetime.now(),
                bid_size=quote_data['depth']['buy'][0]['quantity'] if quote_data['depth']['buy'] else None,
                ask_size=quote_data['depth']['sell'][0]['quantity'] if quote_data['depth']['sell'] else None,
                high=Decimal(str(quote_data['ohlc']['high'])),
                low=Decimal(str(quote_data['ohlc']['low'])),
                open=Decimal(str(quote_data['ohlc']['open'])),
                close=Decimal(str(quote_data['ohlc']['close']))
            )
            
        except Exception as e:
            raise MarketDataError(f"Failed to get quote for {symbol}: {str(e)}", self.broker_name)
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        
        try:
            # Get instrument keys for all symbols
            instrument_keys = []
            symbol_map = {}
            
            for symbol in symbols:
                key = await self._get_instrument_key(symbol)
                instrument_keys.append(key)
                symbol_map[key] = symbol
            
            # Get quotes in batches (Upstox has limits)
            batch_size = 100
            for i in range(0, len(instrument_keys), batch_size):
                batch = instrument_keys[i:i+batch_size]
                keys_param = ','.join(batch)
                
                result = await self._api_call('GET', f'/market-quote/quotes?instrument_key={keys_param}')
                
                for key, quote_data in result['data'].items():
                    symbol = symbol_map[key]
                    quotes[symbol] = Quote(
                        symbol=symbol,
                        bid=Decimal(str(quote_data['depth']['buy'][0]['price'])) if quote_data['depth']['buy'] else None,
                        ask=Decimal(str(quote_data['depth']['sell'][0]['price'])) if quote_data['depth']['sell'] else None,
                        last=Decimal(str(quote_data['last_price'])),
                        volume=quote_data['volume'],
                        timestamp=datetime.now(),
                        bid_size=quote_data['depth']['buy'][0]['quantity'] if quote_data['depth']['buy'] else None,
                        ask_size=quote_data['depth']['sell'][0]['quantity'] if quote_data['depth']['sell'] else None,
                        high=Decimal(str(quote_data['ohlc']['high'])),
                        low=Decimal(str(quote_data['ohlc']['low'])),
                        open=Decimal(str(quote_data['ohlc']['open'])),
                        close=Decimal(str(quote_data['ohlc']['close']))
                    )
            
            return quotes
            
        except Exception as e:
            raise MarketDataError(f"Failed to get quotes: {str(e)}", self.broker_name)
    
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
            instrument_key = await self._get_instrument_key(symbol)
            
            # Set default dates if not provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Map period to Upstox format
            interval_map = {
                '1m': '1minute',
                '5m': '5minute',
                '15m': '15minute',
                '30m': '30minute',
                '1h': '60minute',
                '1d': 'day',
                '1w': 'week',
                '1M': 'month'
            }
            
            interval = interval_map.get(period, 'day')
            
            params = {
                'instrument_key': instrument_key,
                'interval': interval,
                'from_date': start_date.strftime('%Y-%m-%d'),
                'to_date': end_date.strftime('%Y-%m-%d')
            }
            
            result = await self._api_call('GET', '/historical-candle', params)
            
            bars = []
            for candle in result['data']['candles']:
                bars.append(HistoricalBar(
                    timestamp=datetime.fromisoformat(candle[0]),
                    open=Decimal(str(candle[1])),
                    high=Decimal(str(candle[2])),
                    low=Decimal(str(candle[3])),
                    close=Decimal(str(candle[4])),
                    volume=candle[5]
                ))
            
            return bars
            
        except Exception as e:
            raise MarketDataError(f"Failed to get historical data: {str(e)}", self.broker_name)
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place a trading order"""
        try:
            self._validate_order_request(order)
            
            # Map order types to Upstox format
            order_type_map = {
                OrderType.MARKET: 'MARKET',
                OrderType.LIMIT: 'LIMIT',
                OrderType.STOP_LIMIT: 'SL'
            }
            
            side_map = {
                OrderSide.BUY: 'BUY',
                OrderSide.SELL: 'SELL'
            }
            
            instrument_key = await self._get_instrument_key(order.symbol)
            
            order_data = {
                'quantity': order.quantity,
                'product': 'D',  # Delivery
                'validity': 'DAY',
                'price': float(order.price) if order.price else 0,
                'tag': 'string',
                'instrument_token': instrument_key,
                'order_type': order_type_map[order.order_type],
                'transaction_type': side_map[order.side],
                'disclosed_quantity': 0,
                'trigger_price': float(order.stop_price) if order.stop_price else 0,
                'is_amo': False
            }
            
            result = await self._api_call('POST', '/order/place', order_data)
            
            return OrderResponse(
                order_id=result['data']['order_id'],
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
            await self._api_call('DELETE', f'/order/cancel?order_id={order_id}')
            return True
            
        except Exception as e:
            raise OrderError(f"Failed to cancel order: {str(e)}", self.broker_name)
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order"""
        try:
            result = await self._api_call('GET', f'/order/details?order_id={order_id}')
            order_data = result['data']
            
            status_map = {
                'PENDING': OrderStatus.SUBMITTED,
                'OPEN': OrderStatus.SUBMITTED,
                'COMPLETE': OrderStatus.FILLED,
                'CANCELLED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED
            }
            
            return OrderResponse(
                order_id=order_data['order_id'],
                status=status_map.get(order_data['status'], OrderStatus.PENDING),
                symbol=order_data['instrument_token'],
                quantity=order_data['quantity'],
                filled_quantity=order_data['filled_quantity'],
                average_fill_price=Decimal(str(order_data['average_price'])) if order_data['average_price'] else None,
                timestamp=datetime.fromisoformat(order_data['order_timestamp']),
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
            result = await self._api_call('GET', '/order/retrieve-all')
            orders = []
            
            status_map = {
                'PENDING': OrderStatus.SUBMITTED,
                'OPEN': OrderStatus.SUBMITTED,
                'COMPLETE': OrderStatus.FILLED,
                'CANCELLED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED
            }
            
            for order_data in result['data']:
                order_status = status_map.get(order_data['status'], OrderStatus.PENDING)
                
                # Filter by status if specified
                if status and order_status != status:
                    continue
                
                # Filter by date range if specified
                order_time = datetime.fromisoformat(order_data['order_timestamp'])
                if start_date and order_time < start_date:
                    continue
                if end_date and order_time > end_date:
                    continue
                
                orders.append(OrderResponse(
                    order_id=order_data['order_id'],
                    status=order_status,
                    symbol=order_data['instrument_token'],
                    quantity=order_data['quantity'],
                    filled_quantity=order_data['filled_quantity'],
                    average_fill_price=Decimal(str(order_data['average_price'])) if order_data['average_price'] else None,
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
            instrument_key = await self._get_instrument_key(underlying_symbol)
            
            params = {
                'instrument_key': instrument_key
            }
            
            if expiration_date:
                params['expiry'] = expiration_date.strftime('%Y-%m-%d')
            
            result = await self._api_call('GET', '/option/chain', params)
            return result['data']
            
        except Exception as e:
            raise MarketDataError(f"Failed to get options chain: {str(e)}", self.broker_name)
    
    async def _get_instrument_key(self, symbol: str) -> str:
        """Get instrument key for symbol"""
        # This is a simplified implementation
        # In practice, you would maintain a mapping of symbols to instrument keys
        # or fetch from Upstox's master contract file
        
        # For demo purposes, create a mock instrument key
        # Format: NSE_EQ|INE002A01018 (for NSE equity)
        return f"NSE_EQ|{symbol}"
    
    def _validate_symbol(self, symbol: str) -> str:
        """Validate and normalize symbol format for Indian markets"""
        symbol = symbol.upper().strip()
        
        # Remove any exchange suffix for Upstox
        if symbol.endswith('.NS'):
            symbol = symbol[:-3]
        elif symbol.endswith('.BSE'):
            symbol = symbol[:-4]
        
        return symbol