"""
Angel One API Integration
Official Python client for Angel One Connect API (formerly Angel Broking)
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import aiohttp
import json
import hashlib
import hmac
from urllib.parse import urlencode

from .base_broker import (
    BaseBroker, BrokerCredentials, Quote, Position, OrderRequest, OrderResponse, 
    AccountInfo, HistoricalBar, OrderType, OrderSide, OrderStatus, AssetType,
    BrokerException, ConnectionError, AuthenticationError, OrderError, MarketDataError
)

logger = logging.getLogger(__name__)


class AngelOneBroker(BaseBroker):
    """Angel One API broker implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self.base_url = "https://apiconnect.angelbroking.com"
        self.session = None
        self.jwt_token = None
        self.refresh_token = None
        self.user_id = None
        
        # Angel One specific credentials
        self.api_key = credentials.api_key
        self.password = credentials.secret_key
        self.client_code = credentials.additional_params.get('client_code') if credentials.additional_params else None
        self.totp = credentials.additional_params.get('totp') if credentials.additional_params else None
        
        # Rate limiting
        self.rate_limit_calls = 0
        self.rate_limit_window = datetime.now()
        self.max_calls_per_second = 10
    
    @property
    def broker_name(self) -> str:
        return "Angel One"
    
    @property
    def supported_asset_types(self) -> List[AssetType]:
        return [AssetType.STOCK, AssetType.ETF, AssetType.OPTION, AssetType.MUTUAL_FUND]
    
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [OrderType.MARKET, OrderType.LIMIT, OrderType.STOP, OrderType.STOP_LIMIT]
    
    async def connect(self) -> bool:
        """Establish connection to Angel One API"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Generate JWT token
            await self._authenticate()
            
            # Validate session
            await self._validate_session()
            
            self.is_connected = True
            logger.info(f"Connected to Angel One API for user: {self.user_id}")
            return True
            
        except Exception as e:
            self._handle_error(e, "Connection failed")
            if self.session:
                await self.session.close()
            raise ConnectionError(f"Failed to connect to Angel One: {str(e)}")
    
    async def disconnect(self) -> bool:
        """Disconnect from Angel One API"""
        try:
            # Logout to invalidate tokens
            if self.jwt_token:
                await self._logout()
            
            if self.session:
                await self.session.close()
                self.session = None
            
            self.is_connected = False
            self.jwt_token = None
            self.refresh_token = None
            logger.info("Disconnected from Angel One API")
            return True
            
        except Exception as e:
            self._handle_error(e, "Disconnection failed")
            return False
    
    async def _authenticate(self):
        """Authenticate with Angel One API"""
        try:
            login_url = f"{self.base_url}/rest/auth/angelbroking/user/v1/loginByPassword"
            
            login_data = {
                'clientcode': self.client_code,
                'password': self.password,
                'totp': self.totp
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': self.api_key
            }
            
            async with self.session.post(login_url, json=login_data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('status'):
                        self.jwt_token = result['data']['jwtToken']
                        self.refresh_token = result['data']['refreshToken']
                        self.user_id = self.client_code
                    else:
                        raise AuthenticationError(f"Login failed: {result.get('message')}")
                else:
                    raise AuthenticationError(f"Authentication failed: {response.status}")
                    
        except Exception as e:
            raise AuthenticationError(f"Failed to authenticate: {str(e)}")
    
    async def _logout(self):
        """Logout and invalidate tokens"""
        try:
            logout_url = f"{self.base_url}/rest/auth/angelbroking/user/v1/logout"
            headers = self._get_headers()
            
            logout_data = {
                'clientcode': self.client_code
            }
            
            async with self.session.post(logout_url, json=logout_data, headers=headers) as response:
                pass  # Ignore response for logout
                
        except Exception as e:
            logger.warning(f"Logout failed: {str(e)}")
    
    async def _validate_session(self):
        """Validate current session"""
        try:
            headers = self._get_headers()
            
            async with self.session.get(
                f"{self.base_url}/rest/auth/angelbroking/user/v1/getProfile",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('status'):
                        self.user_id = result['data']['clientcode']
                    else:
                        raise AuthenticationError(f"Session validation failed: {result.get('message')}")
                else:
                    raise AuthenticationError(f"Session validation failed: {response.status}")
                    
        except Exception as e:
            raise AuthenticationError(f"Session validation failed: {str(e)}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers"""
        if not self.jwt_token:
            raise AuthenticationError("No JWT token available")
        
        return {
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': '127.0.0.1',
            'X-ClientPublicIP': '127.0.0.1',
            'X-MACAddress': '00:00:00:00:00:00',
            'X-PrivateKey': self.api_key
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
            
            if response.status == 200 and result.get('status'):
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
            # Get RMS limits (funds)
            result = await self._api_call('GET', '/rest/auth/angelbroking/user/v1/getRMS')
            rms_data = result['data']
            
            return AccountInfo(
                account_id=self.user_id,
                buying_power=Decimal(str(rms_data.get('availablecash', 0))),
                cash=Decimal(str(rms_data.get('availablecash', 0))),
                equity=Decimal(str(rms_data.get('net', 0))),
                day_trading_buying_power=Decimal(str(rms_data.get('availablemargin', 0))),
                maintenance_margin=Decimal(str(rms_data.get('utilisedmargin', 0))),
                currency="INR"
            )
            
        except Exception as e:
            raise BrokerException(f"Failed to get account info: {str(e)}", self.broker_name)
    
    async def get_positions(self) -> List[Position]:
        """Get all account positions"""
        try:
            result = await self._api_call('GET', '/rest/auth/angelbroking/order/v1/getPosition')
            positions = []
            
            for pos_data in result['data']:
                if pos_data['netqty'] != '0':  # Only non-zero positions
                    positions.append(Position(
                        symbol=pos_data['tradingsymbol'],
                        quantity=Decimal(str(pos_data['netqty'])),
                        average_price=Decimal(str(pos_data['netprice'])),
                        current_price=Decimal(str(pos_data['ltp'])),
                        market_value=Decimal(str(float(pos_data['netqty']) * float(pos_data['ltp']))),
                        unrealized_pnl=Decimal(str(pos_data['unrealised'])),
                        asset_type=AssetType.STOCK,
                        side="long" if float(pos_data['netqty']) > 0 else "short"
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
            # Get LTP (Last Traded Price)
            ltp_data = {
                'exchange': 'NSE',
                'tradingsymbol': symbol,
                'symboltoken': await self._get_symbol_token(symbol)
            }
            
            result = await self._api_call('POST', '/rest/auth/angelbroking/order/v1/getLTP', ltp_data)
            ltp_info = result['data']
            
            # Get market depth for bid/ask
            depth_data = {
                'exchange': 'NSE',
                'tradingsymbol': symbol,
                'symboltoken': await self._get_symbol_token(symbol)
            }
            
            depth_result = await self._api_call('POST', '/rest/auth/angelbroking/market/v1/getMarketDepth', depth_data)
            depth_info = depth_result['data']
            
            return Quote(
                symbol=symbol,
                bid=Decimal(str(depth_info['buy'][0]['price'])) if depth_info.get('buy') else None,
                ask=Decimal(str(depth_info['sell'][0]['price'])) if depth_info.get('sell') else None,
                last=Decimal(str(ltp_info['ltp'])),
                volume=depth_info.get('totBuyQuan', 0) + depth_info.get('totSellQuan', 0),
                timestamp=datetime.now(),
                bid_size=depth_info['buy'][0]['quantity'] if depth_info.get('buy') else None,
                ask_size=depth_info['sell'][0]['quantity'] if depth_info.get('sell') else None,
                high=Decimal(str(ltp_info.get('high', 0))),
                low=Decimal(str(ltp_info.get('low', 0))),
                open=Decimal(str(ltp_info.get('open', 0))),
                close=Decimal(str(ltp_info.get('close', 0)))
            )
            
        except Exception as e:
            raise MarketDataError(f"Failed to get quote for {symbol}: {str(e)}", self.broker_name)
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        
        # Angel One may require individual calls for each symbol
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
            
            # Map period to Angel One format
            interval_map = {
                '1m': 'ONE_MINUTE',
                '5m': 'FIVE_MINUTE',
                '15m': 'FIFTEEN_MINUTE',
                '30m': 'THIRTY_MINUTE',
                '1h': 'ONE_HOUR',
                '1d': 'ONE_DAY'
            }
            
            interval = interval_map.get(period, 'ONE_DAY')
            
            data = {
                'exchange': 'NSE',
                'symboltoken': await self._get_symbol_token(symbol),
                'interval': interval,
                'fromdate': start_date.strftime('%Y-%m-%d %H:%M'),
                'todate': end_date.strftime('%Y-%m-%d %H:%M')
            }
            
            result = await self._api_call('POST', '/rest/auth/angelbroking/historical/v1/getCandleData', data)
            
            bars = []
            for candle in result['data']:
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
            
            # Map order types to Angel One format
            order_type_map = {
                OrderType.MARKET: 'MARKET',
                OrderType.LIMIT: 'LIMIT',
                OrderType.STOP: 'STOPLOSS_MARKET',
                OrderType.STOP_LIMIT: 'STOPLOSS_LIMIT'
            }
            
            side_map = {
                OrderSide.BUY: 'BUY',
                OrderSide.SELL: 'SELL'
            }
            
            order_data = {
                'variety': 'NORMAL',
                'tradingsymbol': order.symbol,
                'symboltoken': await self._get_symbol_token(order.symbol),
                'transactiontype': side_map[order.side],
                'exchange': 'NSE',
                'ordertype': order_type_map[order.order_type],
                'producttype': 'DELIVERY',
                'duration': 'DAY',
                'price': str(order.price) if order.price else '0',
                'squareoff': '0',
                'stoploss': str(order.stop_price) if order.stop_price else '0',
                'quantity': str(order.quantity)
            }
            
            result = await self._api_call('POST', '/rest/auth/angelbroking/order/v1/placeOrder', order_data)
            
            return OrderResponse(
                order_id=result['data']['orderid'],
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
            data = {
                'variety': 'NORMAL',
                'orderid': order_id
            }
            
            await self._api_call('POST', '/rest/auth/angelbroking/order/v1/cancelOrder', data)
            return True
            
        except Exception as e:
            raise OrderError(f"Failed to cancel order: {str(e)}", self.broker_name)
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order"""
        try:
            result = await self._api_call('GET', '/rest/auth/angelbroking/order/v1/getOrderBook')
            
            for order_data in result['data']:
                if order_data['orderid'] == order_id:
                    status_map = {
                        'open': OrderStatus.SUBMITTED,
                        'complete': OrderStatus.FILLED,
                        'cancelled': OrderStatus.CANCELLED,
                        'rejected': OrderStatus.REJECTED
                    }
                    
                    return OrderResponse(
                        order_id=order_data['orderid'],
                        status=status_map.get(order_data['status'].lower(), OrderStatus.PENDING),
                        symbol=order_data['tradingsymbol'],
                        quantity=int(order_data['quantity']),
                        filled_quantity=int(order_data['filledshares']),
                        average_fill_price=Decimal(str(order_data['averageprice'])) if order_data['averageprice'] else None,
                        timestamp=datetime.fromisoformat(order_data['orderdate']),
                        commission=None
                    )
            
            raise OrderError(f"Order {order_id} not found", self.broker_name)
            
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
            result = await self._api_call('GET', '/rest/auth/angelbroking/order/v1/getOrderBook')
            orders = []
            
            status_map = {
                'open': OrderStatus.SUBMITTED,
                'complete': OrderStatus.FILLED,
                'cancelled': OrderStatus.CANCELLED,
                'rejected': OrderStatus.REJECTED
            }
            
            for order_data in result['data']:
                order_status = status_map.get(order_data['status'].lower(), OrderStatus.PENDING)
                
                # Filter by status if specified
                if status and order_status != status:
                    continue
                
                # Filter by date range if specified
                order_time = datetime.fromisoformat(order_data['orderdate'])
                if start_date and order_time < start_date:
                    continue
                if end_date and order_time > end_date:
                    continue
                
                orders.append(OrderResponse(
                    order_id=order_data['orderid'],
                    status=order_status,
                    symbol=order_data['tradingsymbol'],
                    quantity=int(order_data['quantity']),
                    filled_quantity=int(order_data['filledshares']),
                    average_fill_price=Decimal(str(order_data['averageprice'])) if order_data['averageprice'] else None,
                    timestamp=order_time,
                    commission=None
                ))
            
            return orders
            
        except Exception as e:
            raise OrderError(f"Failed to get orders: {str(e)}", self.broker_name)
    
    async def _get_symbol_token(self, symbol: str) -> str:
        """Get symbol token for trading symbol"""
        # This is a simplified implementation
        # In practice, you would maintain a mapping of symbols to tokens
        # or fetch from Angel One's master contract file
        
        # For demo purposes, return a mock token
        # In production, implement proper symbol-to-token mapping
        return "1234"  # Mock token
    
    def _validate_symbol(self, symbol: str) -> str:
        """Validate and normalize symbol format for Indian markets"""
        symbol = symbol.upper().strip()
        
        # Remove any exchange suffix for Angel One
        if symbol.endswith('.NS'):
            symbol = symbol[:-3]
        elif symbol.endswith('.BSE'):
            symbol = symbol[:-4]
        
        return symbol