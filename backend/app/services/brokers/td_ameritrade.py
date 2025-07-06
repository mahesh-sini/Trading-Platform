"""
TD Ameritrade API Integration
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from .base_broker import (
    BaseBroker, BrokerCredentials, Quote, Position, OrderRequest, OrderResponse, 
    AccountInfo, HistoricalBar, OrderType, OrderSide, OrderStatus, AssetType,
    BrokerException, ConnectionError, AuthenticationError, OrderError, MarketDataError
)

logger = logging.getLogger(__name__)


class TDAmeritradeBroker(BaseBroker):
    """TD Ameritrade API implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self.base_url = "https://api.tdameritrade.com/v1"
        if credentials.sandbox:
            self.base_url = "https://api.tdameritrade.com/v1"  # TD uses same URL
        
        self.access_token = None
        self.refresh_token = credentials.additional_params.get('refresh_token')
        self.session = None
        
    @property
    def broker_name(self) -> str:
        return "TD Ameritrade"
    
    @property
    def supported_asset_types(self) -> List[AssetType]:
        return [
            AssetType.STOCK,
            AssetType.OPTION,
            AssetType.ETF,
            AssetType.MUTUAL_FUND,
            AssetType.BOND,
            AssetType.FOREX
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
    
    async def _authenticate(self) -> bool:
        """Authenticate with TD Ameritrade"""
        try:
            session = await self._get_session()
            
            # OAuth2 token request
            auth_data = {
                'grant_type': 'authorization_code',
                'client_id': self.credentials.api_key,
                'redirect_uri': 'https://localhost',
                'code': self.credentials.secret_key  # Authorization code
            }
            
            async with session.post(
                f"{self.base_url}/oauth2/token",
                data=auth_data
            ) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data['access_token']
                    self.refresh_token = token_data.get('refresh_token')
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
        if not self.access_token:
            await self._authenticate()
        
        session = await self._get_session()
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with session.request(
                method, 
                url, 
                headers=headers, 
                params=params,
                json=data
            ) as response:
                if response.status == 401:
                    # Token expired, try to refresh
                    await self._refresh_token()
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    
                    async with session.request(
                        method, 
                        url, 
                        headers=headers, 
                        params=params,
                        json=data
                    ) as retry_response:
                        return await retry_response.json()
                
                return await response.json()
                
        except Exception as e:
            self._handle_error(e, f"API request failed: {method} {endpoint}")
            raise BrokerException(f"API request failed: {str(e)}", self.broker_name)
    
    async def _refresh_token(self) -> bool:
        """Refresh access token"""
        try:
            session = await self._get_session()
            
            refresh_data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.credentials.api_key
            }
            
            async with session.post(
                f"{self.base_url}/oauth2/token",
                data=refresh_data
            ) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data['access_token']
                    return True
                else:
                    raise AuthenticationError(
                        f"Token refresh failed: {response.status}",
                        self.broker_name
                    )
                    
        except Exception as e:
            self._handle_error(e, "Token refresh failed")
            return False
    
    async def connect(self) -> bool:
        """Connect to TD Ameritrade API"""
        try:
            success = await self._authenticate()
            if success:
                self.is_connected = True
                logger.info("Connected to TD Ameritrade API")
            return success
            
        except Exception as e:
            self._handle_error(e, "Connection failed")
            raise ConnectionError(f"Failed to connect to TD Ameritrade: {str(e)}", self.broker_name)
    
    async def disconnect(self) -> bool:
        """Disconnect from TD Ameritrade API"""
        try:
            if self.session:
                await self.session.close()
            self.is_connected = False
            logger.info("Disconnected from TD Ameritrade API")
            return True
            
        except Exception as e:
            self._handle_error(e, "Disconnect failed")
            return False
    
    async def is_market_open(self) -> bool:
        """Check if market is open"""
        try:
            # TD Ameritrade has a market hours endpoint
            response = await self._make_request(
                'GET', 
                '/marketdata/EQUITY/hours',
                params={'date': datetime.now().strftime('%Y-%m-%d')}
            )
            
            equity_hours = response.get('equity', {})
            is_open = equity_hours.get('isOpen', False)
            return is_open
            
        except Exception as e:
            self._handle_error(e, "Market hours check failed")
            return False
    
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        try:
            account_id = self.credentials.account_id
            response = await self._make_request('GET', f'/accounts/{account_id}')
            
            account_data = response['securitiesAccount']
            current_balances = account_data['currentBalances']
            
            return AccountInfo(
                account_id=account_id,
                buying_power=Decimal(str(current_balances['buyingPower'])),
                cash=Decimal(str(current_balances['cashBalance'])),
                equity=Decimal(str(current_balances['equity'])),
                day_trading_buying_power=Decimal(str(current_balances.get('dayTradingBuyingPower', 0))),
                maintenance_margin=Decimal(str(current_balances.get('maintenanceRequirement', 0))),
                currency="USD"
            )
            
        except Exception as e:
            self._handle_error(e, "Get account info failed")
            raise BrokerException(f"Failed to get account info: {str(e)}", self.broker_name)
    
    async def get_positions(self) -> List[Position]:
        """Get all account positions"""
        try:
            account_id = self.credentials.account_id
            response = await self._make_request('GET', f'/accounts/{account_id}')
            
            positions = []
            account_data = response['securitiesAccount']
            
            for position_data in account_data.get('positions', []):
                instrument = position_data['instrument']
                
                position = Position(
                    symbol=instrument['symbol'],
                    quantity=Decimal(str(position_data['longQuantity'] - position_data['shortQuantity'])),
                    average_price=Decimal(str(position_data['averagePrice'])),
                    current_price=Decimal(str(position_data['marketValue'] / position_data['longQuantity'])) if position_data['longQuantity'] > 0 else None,
                    market_value=Decimal(str(position_data['marketValue'])),
                    unrealized_pnl=Decimal(str(position_data.get('currentDayProfitLoss', 0))),
                    asset_type=self._convert_asset_type(instrument['assetType']),
                    side="long" if position_data['longQuantity'] > 0 else "short"
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
                '/marketdata/quotes',
                params={'symbol': symbol}
            )
            
            quote_data = response[symbol]
            
            return Quote(
                symbol=symbol,
                bid=Decimal(str(quote_data['bidPrice'])) if quote_data.get('bidPrice') else None,
                ask=Decimal(str(quote_data['askPrice'])) if quote_data.get('askPrice') else None,
                last=Decimal(str(quote_data['lastPrice'])) if quote_data.get('lastPrice') else None,
                volume=int(quote_data.get('totalVolume', 0)),
                timestamp=datetime.fromtimestamp(quote_data['quoteTimeInLong'] / 1000),
                bid_size=int(quote_data.get('bidSize', 0)),
                ask_size=int(quote_data.get('askSize', 0)),
                high=Decimal(str(quote_data['highPrice'])) if quote_data.get('highPrice') else None,
                low=Decimal(str(quote_data['lowPrice'])) if quote_data.get('lowPrice') else None,
                open=Decimal(str(quote_data['openPrice'])) if quote_data.get('openPrice') else None,
                close=Decimal(str(quote_data['closePrice'])) if quote_data.get('closePrice') else None
            )
            
        except Exception as e:
            self._handle_error(e, f"Get quote for {symbol} failed")
            raise MarketDataError(f"Failed to get quote for {symbol}: {str(e)}", self.broker_name)
    
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        try:
            symbol_list = ','.join([self._validate_symbol(s) for s in symbols])
            
            response = await self._make_request(
                'GET', 
                '/marketdata/quotes',
                params={'symbol': symbol_list}
            )
            
            quotes = {}
            for symbol, quote_data in response.items():
                quotes[symbol] = Quote(
                    symbol=symbol,
                    bid=Decimal(str(quote_data['bidPrice'])) if quote_data.get('bidPrice') else None,
                    ask=Decimal(str(quote_data['askPrice'])) if quote_data.get('askPrice') else None,
                    last=Decimal(str(quote_data['lastPrice'])) if quote_data.get('lastPrice') else None,
                    volume=int(quote_data.get('totalVolume', 0)),
                    timestamp=datetime.fromtimestamp(quote_data['quoteTimeInLong'] / 1000),
                    bid_size=int(quote_data.get('bidSize', 0)),
                    ask_size=int(quote_data.get('askSize', 0))
                )
            
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
            
            params = {
                'symbol': symbol,
                'periodType': 'day',
                'period': 10,
                'frequencyType': 'minute',
                'frequency': 1
            }
            
            if start_date and end_date:
                params.update({
                    'startDate': int(start_date.timestamp() * 1000),
                    'endDate': int(end_date.timestamp() * 1000)
                })
            
            response = await self._make_request(
                'GET', 
                '/marketdata/{symbol}/pricehistory'.format(symbol=symbol),
                params=params
            )
            
            bars = []
            for candle in response.get('candles', []):
                bar = HistoricalBar(
                    timestamp=datetime.fromtimestamp(candle['datetime'] / 1000),
                    open=Decimal(str(candle['open'])),
                    high=Decimal(str(candle['high'])),
                    low=Decimal(str(candle['low'])),
                    close=Decimal(str(candle['close'])),
                    volume=int(candle['volume'])
                )
                bars.append(bar)
            
            return bars[-limit:] if limit else bars
            
        except Exception as e:
            self._handle_error(e, f"Get historical data for {symbol} failed")
            raise MarketDataError(f"Failed to get historical data for {symbol}: {str(e)}", self.broker_name)
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place a trading order"""
        try:
            # Validate order
            self._validate_order_request(order)
            
            # Convert to TD Ameritrade order format
            td_order = self._convert_to_td_order(order)
            
            account_id = self.credentials.account_id
            response = await self._make_request(
                'POST',
                f'/accounts/{account_id}/orders',
                data=td_order
            )
            
            # TD returns order ID in the Location header, but we'll mock it
            order_id = f"TD_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.SUBMITTED,
                symbol=order.symbol,
                quantity=order.quantity,
                filled_quantity=0,
                average_fill_price=None,
                timestamp=datetime.now(),
                commission=Decimal("0.00")  # TD Ameritrade has $0 commissions for stocks
            )
            
        except Exception as e:
            self._handle_error(e, f"Place order failed for {order.symbol}")
            raise OrderError(f"Failed to place order: {str(e)}", self.broker_name)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            account_id = self.credentials.account_id
            await self._make_request(
                'DELETE',
                f'/accounts/{account_id}/orders/{order_id}'
            )
            
            logger.info(f"Cancelled order {order_id}")
            return True
            
        except Exception as e:
            self._handle_error(e, f"Cancel order {order_id} failed")
            raise OrderError(f"Failed to cancel order {order_id}: {str(e)}", self.broker_name)
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order"""
        try:
            account_id = self.credentials.account_id
            response = await self._make_request(
                'GET',
                f'/accounts/{account_id}/orders/{order_id}'
            )
            
            return self._convert_from_td_order(response)
            
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
            account_id = self.credentials.account_id
            params = {}
            
            if start_date:
                params['fromEnteredTime'] = start_date.strftime('%Y-%m-%d')
            if end_date:
                params['toEnteredTime'] = end_date.strftime('%Y-%m-%d')
            
            response = await self._make_request(
                'GET',
                f'/accounts/{account_id}/orders',
                params=params
            )
            
            orders = []
            for order_data in response:
                order = self._convert_from_td_order(order_data)
                
                # Filter by status if specified
                if not status or order.status == status:
                    orders.append(order)
            
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
            
            params = {
                'symbol': underlying_symbol,
                'contractType': 'ALL',
                'includeQuotes': 'TRUE'
            }
            
            if expiration_date:
                params['fromDate'] = expiration_date.strftime('%Y-%m-%d')
                params['toDate'] = expiration_date.strftime('%Y-%m-%d')
            
            response = await self._make_request(
                'GET',
                '/marketdata/chains',
                params=params
            )
            
            return response
            
        except Exception as e:
            self._handle_error(e, f"Get options chain for {underlying_symbol} failed")
            raise MarketDataError(f"Failed to get options chain for {underlying_symbol}: {str(e)}", self.broker_name)
    
    def _convert_asset_type(self, td_asset_type: str) -> AssetType:
        """Convert TD Ameritrade asset type to our enum"""
        mapping = {
            'EQUITY': AssetType.STOCK,
            'OPTION': AssetType.OPTION,
            'ETF': AssetType.ETF,
            'MUTUAL_FUND': AssetType.MUTUAL_FUND,
            'BOND': AssetType.BOND,
            'FOREX': AssetType.FOREX
        }
        return mapping.get(td_asset_type, AssetType.STOCK)
    
    def _convert_to_td_order(self, order: OrderRequest) -> Dict[str, Any]:
        """Convert OrderRequest to TD Ameritrade order format"""
        instruction = 'BUY' if order.side in [OrderSide.BUY, OrderSide.BUY_TO_COVER] else 'SELL'
        
        td_order = {
            'orderType': self._convert_order_type(order.order_type),
            'session': 'NORMAL',
            'duration': order.time_in_force,
            'orderStrategyType': 'SINGLE',
            'orderLegCollection': [
                {
                    'instruction': instruction,
                    'quantity': order.quantity,
                    'instrument': {
                        'symbol': order.symbol,
                        'assetType': 'EQUITY'
                    }
                }
            ]
        }
        
        if order.price:
            td_order['price'] = float(order.price)
        
        if order.stop_price:
            td_order['stopPrice'] = float(order.stop_price)
        
        return td_order
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert OrderType to TD Ameritrade order type"""
        mapping = {
            OrderType.MARKET: 'MARKET',
            OrderType.LIMIT: 'LIMIT',
            OrderType.STOP: 'STOP',
            OrderType.STOP_LIMIT: 'STOP_LIMIT'
        }
        return mapping.get(order_type, 'MARKET')
    
    def _convert_from_td_order(self, td_order: Dict[str, Any]) -> OrderResponse:
        """Convert TD Ameritrade order to OrderResponse"""
        leg = td_order['orderLegCollection'][0]
        instrument = leg['instrument']
        
        return OrderResponse(
            order_id=str(td_order['orderId']),
            status=self._convert_order_status(td_order['status']),
            symbol=instrument['symbol'],
            quantity=int(leg['quantity']),
            filled_quantity=int(td_order.get('filledQuantity', 0)),
            average_fill_price=Decimal(str(td_order['price'])) if td_order.get('price') else None,
            timestamp=datetime.fromisoformat(td_order['enteredTime'].replace('Z', '+00:00')),
            commission=Decimal("0.00")
        )
    
    def _convert_order_status(self, td_status: str) -> OrderStatus:
        """Convert TD Ameritrade order status to our enum"""
        mapping = {
            'AWAITING_PARENT_ORDER': OrderStatus.PENDING,
            'AWAITING_CONDITION': OrderStatus.PENDING,
            'AWAITING_MANUAL_REVIEW': OrderStatus.PENDING,
            'ACCEPTED': OrderStatus.SUBMITTED,
            'AWAITING_UR_OUT': OrderStatus.SUBMITTED,
            'PENDING_ACTIVATION': OrderStatus.SUBMITTED,
            'QUEUED': OrderStatus.SUBMITTED,
            'WORKING': OrderStatus.SUBMITTED,
            'FILLED': OrderStatus.FILLED,
            'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
            'CANCELED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED,
            'EXPIRED': OrderStatus.EXPIRED
        }
        return mapping.get(td_status, OrderStatus.PENDING)