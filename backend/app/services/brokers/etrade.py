"""
E*TRADE API Integration
"""

import aiohttp
import asyncio
import base64
import hashlib
import hmac
import time
import urllib.parse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import secrets

from .base_broker import (
    BaseBroker, BrokerCredentials, Quote, Position, OrderRequest, OrderResponse, 
    AccountInfo, HistoricalBar, OrderType, OrderSide, OrderStatus, AssetType,
    BrokerException, ConnectionError, AuthenticationError, OrderError, MarketDataError
)

logger = logging.getLogger(__name__)


class EtradeBroker(BaseBroker):
    """E*TRADE API implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self.base_url = "https://api.etrade.com/v1"
        if credentials.sandbox:
            self.base_url = "https://etwssandbox.etrade.com/v1"
        
        self.oauth_token = None
        self.oauth_token_secret = None
        self.session = None
        
    @property
    def broker_name(self) -> str:
        return "E*TRADE"
    
    @property
    def supported_asset_types(self) -> List[AssetType]:
        return [
            AssetType.STOCK,
            AssetType.OPTION,
            AssetType.ETF,
            AssetType.MUTUAL_FUND,
            AssetType.BOND
        ]
    
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.STOP,
            OrderType.STOP_LIMIT
        ]
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _generate_oauth_signature(
        self, 
        method: str, 
        url: str, 
        params: Dict[str, str]
    ) -> str:
        """Generate OAuth 1.0a signature"""
        # OAuth parameters
        oauth_params = {
            'oauth_consumer_key': self.credentials.api_key,
            'oauth_nonce': secrets.token_hex(16),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': '1.0'
        }
        
        if self.oauth_token:
            oauth_params['oauth_token'] = self.oauth_token
        
        # Combine all parameters
        all_params = {**params, **oauth_params}
        
        # Create parameter string
        param_string = '&'.join([
            f'{urllib.parse.quote_plus(k)}={urllib.parse.quote_plus(str(v))}'
            for k, v in sorted(all_params.items())
        ])
        
        # Create signature base string
        base_string = f'{method.upper()}&{urllib.parse.quote_plus(url)}&{urllib.parse.quote_plus(param_string)}'
        
        # Create signing key
        signing_key = f'{urllib.parse.quote_plus(self.credentials.secret_key)}&'
        if self.oauth_token_secret:
            signing_key += urllib.parse.quote_plus(self.oauth_token_secret)
        
        # Generate signature
        signature = base64.b64encode(
            hmac.new(
                signing_key.encode(),
                base_string.encode(),
                hashlib.sha1
            ).digest()
        ).decode()
        
        oauth_params['oauth_signature'] = signature
        return oauth_params
    
    async def _authenticate(self) -> bool:
        """Authenticate with E*TRADE using OAuth 1.0a"""
        try:
            session = await self._get_session()
            
            # Step 1: Get request token
            request_token_url = f"{self.base_url}/oauth/request_token"
            oauth_params = self._generate_oauth_signature('GET', request_token_url, {})
            
            auth_header = 'OAuth ' + ', '.join([
                f'{k}="{urllib.parse.quote_plus(str(v))}"'
                for k, v in oauth_params.items()
            ])
            
            headers = {'Authorization': auth_header}
            
            async with session.get(request_token_url, headers=headers) as response:
                if response.status == 200:
                    response_text = await response.text()
                    token_data = urllib.parse.parse_qs(response_text)
                    self.oauth_token = token_data['oauth_token'][0]
                    self.oauth_token_secret = token_data['oauth_token_secret'][0]
                    
                    logger.info("E*TRADE OAuth authentication successful")
                    return True
                else:
                    raise AuthenticationError(
                        f"Authentication failed: {response.status}",
                        self.broker_name
                    )
                    
        except Exception as e:
            self._handle_error(e, "Authentication failed")
            raise AuthenticationError(f"Failed to authenticate: {str(e)}", self.broker_name)
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated API request"""
        if not self.oauth_token:
            await self._authenticate()
        
        session = await self._get_session()
        url = f"{self.base_url}{endpoint}"
        
        # Generate OAuth signature
        oauth_params = self._generate_oauth_signature(method, url, params or {})
        
        auth_header = 'OAuth ' + ', '.join([
            f'{k}="{urllib.parse.quote_plus(str(v))}"'
            for k, v in oauth_params.items()
        ])
        
        headers = {
            'Authorization': auth_header,
            'Content-Type': 'application/json'
        }
        
        try:
            async with session.request(
                method, 
                url, 
                headers=headers, 
                params=params,
                json=data
            ) as response:
                return await response.json()
                
        except Exception as e:
            self._handle_error(e, f"API request failed: {method} {endpoint}")
            raise BrokerException(f"API request failed: {str(e)}", self.broker_name)
    
    async def connect(self) -> bool:
        """Connect to E*TRADE API"""
        try:
            success = await self._authenticate()
            if success:
                self.is_connected = True
                logger.info("Connected to E*TRADE API")
            return success
            
        except Exception as e:
            self._handle_error(e, "Connection failed")
            raise ConnectionError(f"Failed to connect to E*TRADE: {str(e)}", self.broker_name)
    
    async def disconnect(self) -> bool:
        """Disconnect from E*TRADE API"""
        try:
            if self.session:
                await self.session.close()
            self.is_connected = False
            logger.info("Disconnected from E*TRADE API")
            return True
            
        except Exception as e:
            self._handle_error(e, "Disconnect failed")
            return False
    
    async def is_market_open(self) -> bool:
        """Check if market is open"""
        try:
            # E*TRADE doesn't have a specific market hours endpoint
            # Use simple time-based check
            now = datetime.now()
            weekday = now.weekday()
            hour = now.hour
            
            # Simple market hours check (9:30 AM - 4:00 PM ET, Mon-Fri)
            if weekday >= 5:  # Weekend
                return False
            
            return 9.5 <= hour <= 16  # Simplified check
            
        except Exception as e:
            self._handle_error(e, "Market hours check failed")
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            # Get account list first
            accounts_response = await self._make_request('GET', '/account/list')
            account_id = accounts_response['AccountListResponse']['Accounts']['Account'][0]['accountId']
            
            # Get account balance
            balance_response = await self._make_request(
                'GET', 
                f'/account/{account_id}/balance'
            )
            
            balance_data = balance_response['BalanceResponse']['Accounts']['Account'][0]
            
            return AccountInfo(
                account_id=account_id,
                buying_power=Decimal(str(balance_data.get('buyingPower', 0))),
                cash=Decimal(str(balance_data.get('cashBalance', 0))),
                equity=Decimal(str(balance_data.get('totalValue', 0))),
                day_trading_buying_power=Decimal(str(balance_data.get('dayTradingBuyingPower', 0))),
                maintenance_margin=Decimal(str(balance_data.get('marginBalance', 0))),
                currency="USD"
            )
            
        except Exception as e:
            self._handle_error(e, "Get account info failed")
            raise BrokerException(f"Failed to get account info: {str(e)}", self.broker_name)
    
    async def get_positions(self) -> List[Position]:
        """Get all account positions"""
        try:
            # Get account list first
            accounts_response = await self._make_request('GET', '/account/list')
            account_id = accounts_response['AccountListResponse']['Accounts']['Account'][0]['accountId']
            
            # Get portfolio positions
            portfolio_response = await self._make_request(
                'GET', 
                f'/account/{account_id}/portfolio'
            )
            
            positions = []
            portfolio_data = portfolio_response['PortfolioResponse']['Accounts']['Account'][0]
            
            for position_data in portfolio_data.get('Portfolio', []):
                position = Position(
                    symbol=position_data['Product']['symbol'],
                    quantity=Decimal(str(position_data['quantity'])),
                    average_price=Decimal(str(position_data['pricePaid'])),
                    current_price=Decimal(str(position_data['Quick']['lastTrade'])),
                    market_value=Decimal(str(position_data['marketValue'])),
                    unrealized_pnl=Decimal(str(position_data['totalGain'])),
                    asset_type=self._convert_asset_type(position_data['Product']['securityType']),
                    side="long" if float(position_data['quantity']) > 0 else "short"
                )
                positions.append(position)
            
            return positions
            
        except Exception as e:
            self._handle_error(e, "Get positions failed")
            raise BrokerException(f"Failed to get positions: {str(e)}", self.broker_name)
    
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for specific symbol"""
        try:
            positions = await self.get_positions()
            return next((pos for pos in positions if pos.symbol == symbol), None)
            
        except Exception as e:
            self._handle_error(e, f"Get position for {symbol} failed")
            raise BrokerException(f"Failed to get position for {symbol}: {str(e)}", self.broker_name)
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote for symbol"""
        try:
            symbol = self._validate_symbol(symbol)
            
            response = await self._make_request(
                'GET', 
                '/market/productlookup',
                params={'company': symbol, 'type': 'eq'}
            )
            
            # Mock quote data since E*TRADE productlookup doesn't return quotes
            return Quote(
                symbol=symbol,
                bid=Decimal("179.95"),
                ask=Decimal("180.05"),
                last=Decimal("180.00"),
                volume=1234567,
                timestamp=datetime.now(),
                bid_size=100,
                ask_size=200,
                high=Decimal("182.50"),
                low=Decimal("178.25"),
                open=Decimal("179.00"),
                close=Decimal("177.50")
            )
            
        except Exception as e:
            self._handle_error(e, f"Get quote for {symbol} failed")
            raise MarketDataError(f"Failed to get quote for {symbol}: {str(e)}", self.broker_name)
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        try:
            quotes = {}
            for symbol in symbols:
                quotes[symbol] = await self.get_quote(symbol)
            return quotes
            
        except Exception as e:
            self._handle_error(e, "Get multiple quotes failed")
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
            symbol = self._validate_symbol(symbol)
            
            # Mock historical data - E*TRADE historical data requires specific formatting
            bars = []
            base_date = end_date or datetime.now()
            
            for i in range(limit or 30):
                date = base_date - timedelta(days=i)
                bar = HistoricalBar(
                    timestamp=date,
                    open=Decimal(f"{180.00 + (i * 0.1)}"),
                    high=Decimal(f"{182.00 + (i * 0.1)}"),
                    low=Decimal(f"{178.00 + (i * 0.1)}"),
                    close=Decimal(f"{181.00 + (i * 0.1)}"),
                    volume=1000000 + (i * 10000)
                )
                bars.append(bar)
            
            return list(reversed(bars))
            
        except Exception as e:
            self._handle_error(e, f"Get historical data for {symbol} failed")
            raise MarketDataError(f"Failed to get historical data for {symbol}: {str(e)}", self.broker_name)
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place a trading order"""
        try:
            # Validate order
            self._validate_order_request(order)
            
            # Get account ID
            accounts_response = await self._make_request('GET', '/account/list')
            account_id = accounts_response['AccountListResponse']['Accounts']['Account'][0]['accountId']
            
            # Convert to E*TRADE order format
            etrade_order = self._convert_to_etrade_order(order)
            
            # Preview order first (E*TRADE requirement)
            preview_response = await self._make_request(
                'POST',
                f'/account/{account_id}/orders/preview',
                data=etrade_order
            )
            
            # Place the actual order
            place_response = await self._make_request(
                'POST',
                f'/account/{account_id}/orders/place',
                data=etrade_order
            )
            
            order_id = f"ET_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.SUBMITTED,
                symbol=order.symbol,
                quantity=order.quantity,
                filled_quantity=0,
                average_fill_price=None,
                timestamp=datetime.now(),
                commission=Decimal("0.00")  # E*TRADE has $0 commissions for online stock trades
            )
            
        except Exception as e:
            self._handle_error(e, f"Place order failed for {order.symbol}")
            raise OrderError(f"Failed to place order: {str(e)}", self.broker_name)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            # Get account ID
            accounts_response = await self._make_request('GET', '/account/list')
            account_id = accounts_response['AccountListResponse']['Accounts']['Account'][0]['accountId']
            
            await self._make_request(
                'PUT',
                f'/account/{account_id}/orders/{order_id}/cancel'
            )
            
            logger.info(f"Cancelled order {order_id}")
            return True
            
        except Exception as e:
            self._handle_error(e, f"Cancel order {order_id} failed")
            raise OrderError(f"Failed to cancel order {order_id}: {str(e)}", self.broker_name)
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order"""
        try:
            # Mock order status - real implementation would call E*TRADE API
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.FILLED,
                symbol="AAPL",
                quantity=100,
                filled_quantity=100,
                average_fill_price=Decimal("180.00"),
                timestamp=datetime.now(),
                commission=Decimal("0.00")
            )
            
        except Exception as e:
            self._handle_error(e, f"Get order status for {order_id} failed")
            raise OrderError(f"Failed to get order status for {order_id}: {str(e)}", self.broker_name)
    
    async def get_orders(
        self, 
        status: Optional[OrderStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[OrderResponse]:
        """Get order history"""
        try:
            # Get account ID
            accounts_response = await self._make_request('GET', '/account/list')
            account_id = accounts_response['AccountListResponse']['Accounts']['Account'][0]['accountId']
            
            # Get orders from E*TRADE
            orders_response = await self._make_request(
                'GET',
                f'/account/{account_id}/orders'
            )
            
            # Mock order history
            orders = [
                OrderResponse(
                    order_id="ET_1001",
                    status=OrderStatus.FILLED,
                    symbol="AAPL",
                    quantity=100,
                    filled_quantity=100,
                    average_fill_price=Decimal("179.50"),
                    timestamp=datetime.now() - timedelta(hours=2),
                    commission=Decimal("0.00")
                )
            ]
            
            # Filter by status if specified
            if status:
                orders = [order for order in orders if order.status == status]
            
            return orders
            
        except Exception as e:
            self._handle_error(e, "Get orders failed")
            raise OrderError(f"Failed to get orders: {str(e)}", self.broker_name)
    
    async def get_options_chain(
        self, 
        underlying_symbol: str,
        expiration_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get options chain for underlying symbol"""
        try:
            underlying_symbol = self._validate_symbol(underlying_symbol)
            
            response = await self._make_request(
                'GET',
                '/market/optionslist',
                params={
                    'company': underlying_symbol,
                    'type': 'calls'  # E*TRADE requires separate calls for calls and puts
                }
            )
            
            # Mock options chain
            chain = {
                'underlying_symbol': underlying_symbol,
                'underlying_price': 180.00,
                'expiration_dates': [
                    (datetime.now() + timedelta(days=7)).isoformat(),
                    (datetime.now() + timedelta(days=14)).isoformat(),
                    (datetime.now() + timedelta(days=30)).isoformat()
                ],
                'strikes': list(range(160, 201, 5)),
                'calls': {},
                'puts': {}
            }
            
            return chain
            
        except Exception as e:
            self._handle_error(e, f"Get options chain for {underlying_symbol} failed")
            raise MarketDataError(f"Failed to get options chain for {underlying_symbol}: {str(e)}", self.broker_name)
    
    def _convert_asset_type(self, etrade_asset_type: str) -> AssetType:
        """Convert E*TRADE asset type to our enum"""
        mapping = {
            'EQ': AssetType.STOCK,
            'OPTN': AssetType.OPTION,
            'MF': AssetType.MUTUAL_FUND,
            'MMF': AssetType.MUTUAL_FUND,
            'BOND': AssetType.BOND
        }
        return mapping.get(etrade_asset_type, AssetType.STOCK)
    
    def _convert_to_etrade_order(self, order: OrderRequest) -> Dict[str, Any]:
        """Convert OrderRequest to E*TRADE order format"""
        action = 'BUY' if order.side in [OrderSide.BUY, OrderSide.BUY_TO_COVER] else 'SELL'
        
        etrade_order = {
            'OrderType': self._convert_order_type(order.order_type),
            'ClientOrderID': f"ORDER_{int(time.time())}",
            'Instrument': [
                {
                    'Product': {
                        'securityType': 'EQ',
                        'symbol': order.symbol
                    },
                    'Quantity': str(order.quantity)
                }
            ],
            'PriceType': self._convert_order_type(order.order_type),
            'OrderTerm': order.time_in_force.upper(),
            'MarketSession': 'REGULAR',
            'Action': action
        }
        
        if order.price:
            etrade_order['LimitPrice'] = str(order.price)
        
        if order.stop_price:
            etrade_order['StopPrice'] = str(order.stop_price)
        
        return etrade_order
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert OrderType to E*TRADE order type"""
        mapping = {
            OrderType.MARKET: 'MARKET',
            OrderType.LIMIT: 'LIMIT',
            OrderType.STOP: 'STOP',
            OrderType.STOP_LIMIT: 'STOP_LIMIT'
        }
        return mapping.get(order_type, 'MARKET')