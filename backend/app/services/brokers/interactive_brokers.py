"""
Interactive Brokers API Integration
"""

import asyncio
import json
import ssl
import websockets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .base_broker import (
    BaseBroker, BrokerCredentials, Quote, Position, OrderRequest, OrderResponse, 
    AccountInfo, HistoricalBar, OrderType, OrderSide, OrderStatus, AssetType,
    BrokerException, ConnectionError, AuthenticationError, OrderError, MarketDataError
)

logger = logging.getLogger(__name__)


class InteractiveBrokersBroker(BaseBroker):
    """Interactive Brokers API implementation"""
    
    def __init__(self, credentials: BrokerCredentials):
        super().__init__(credentials)
        self.client_id = int(credentials.additional_params.get('client_id', 1))
        self.host = credentials.additional_params.get('host', 'localhost')
        self.port = int(credentials.additional_params.get('port', 7497))  # Paper trading port
        self.websocket = None
        self.request_id = 1000
        self.pending_requests = {}
        
    @property
    def broker_name(self) -> str:
        return "Interactive Brokers"
    
    @property
    def supported_asset_types(self) -> List[AssetType]:
        return [
            AssetType.STOCK,
            AssetType.OPTION,
            AssetType.ETF,
            AssetType.BOND,
            AssetType.FOREX,
            AssetType.MUTUAL_FUND
        ]
    
    @property
    def supported_order_types(self) -> List[OrderType]:
        return [
            OrderType.MARKET,
            OrderType.LIMIT,
            OrderType.STOP,
            OrderType.STOP_LIMIT,
            OrderType.TRAILING_STOP
        ]
    
    def _get_next_request_id(self) -> int:
        """Get next request ID for IB API"""
        self.request_id += 1
        return self.request_id
    
    async def connect(self) -> bool:
        """Connect to IB Gateway/TWS"""
        try:
            # IB uses a REST API gateway for modern integrations
            # This is a simplified connection - real implementation would use IB API
            self.is_connected = True
            logger.info(f"Connected to IB Gateway at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self._handle_error(e, "Connection failed")
            raise ConnectionError(f"Failed to connect to IB: {str(e)}", self.broker_name)
    
    async def disconnect(self) -> bool:
        """Disconnect from IB Gateway/TWS"""
        try:
            if self.websocket:
                await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from IB Gateway")
            return True
            
        except Exception as e:
            self._handle_error(e, "Disconnect failed")
            return False
    
    async def is_market_open(self) -> bool:
        """Check if market is open"""
        try:
            # This would normally query IB for market hours
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
            # Mock data - real implementation would call IB API
            return AccountInfo(
                account_id=self.credentials.account_id or "DU123456",
                buying_power=Decimal("50000.00"),
                cash=Decimal("25000.00"),
                equity=Decimal("75000.00"),
                day_trading_buying_power=Decimal("100000.00"),
                maintenance_margin=Decimal("5000.00"),
                currency="USD"
            )
            
        except Exception as e:
            self._handle_error(e, "Get account info failed")
            raise BrokerException(f"Failed to get account info: {str(e)}", self.broker_name)
    
    async def get_positions(self) -> List[Position]:
        """Get all account positions"""
        try:
            # Mock positions - real implementation would call IB API
            positions = [
                Position(
                    symbol="AAPL",
                    quantity=Decimal("100"),
                    average_price=Decimal("175.50"),
                    current_price=Decimal("180.25"),
                    market_value=Decimal("18025.00"),
                    unrealized_pnl=Decimal("475.00"),
                    asset_type=AssetType.STOCK,
                    side="long"
                ),
                Position(
                    symbol="TSLA",
                    quantity=Decimal("-50"),
                    average_price=Decimal("250.00"),
                    current_price=Decimal("245.00"),
                    market_value=Decimal("-12250.00"),
                    unrealized_pnl=Decimal("250.00"),
                    asset_type=AssetType.STOCK,
                    side="short"
                )
            ]
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
            
            # Mock quote data - real implementation would call IB API
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
            
            # Mock historical data - real implementation would call IB API
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
            
            # Convert order to IB format
            ib_order = self._convert_to_ib_order(order)
            
            # Mock order placement - real implementation would call IB API
            order_id = f"IB_{self._get_next_request_id()}"
            
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.SUBMITTED,
                symbol=order.symbol,
                quantity=order.quantity,
                filled_quantity=0,
                average_fill_price=None,
                timestamp=datetime.now(),
                commission=Decimal("1.00")
            )
            
        except Exception as e:
            self._handle_error(e, f"Place order failed for {order.symbol}")
            raise OrderError(f"Failed to place order: {str(e)}", self.broker_name)
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        try:
            # Mock cancellation - real implementation would call IB API
            logger.info(f"Cancelling order {order_id}")
            return True
            
        except Exception as e:
            self._handle_error(e, f"Cancel order {order_id} failed")
            raise OrderError(f"Failed to cancel order {order_id}: {str(e)}", self.broker_name)
    
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order"""
        try:
            # Mock order status - real implementation would call IB API
            return OrderResponse(
                order_id=order_id,
                status=OrderStatus.FILLED,
                symbol="AAPL",
                quantity=100,
                filled_quantity=100,
                average_fill_price=Decimal("180.00"),
                timestamp=datetime.now(),
                commission=Decimal("1.00")
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
            # Mock order history - real implementation would call IB API
            orders = [
                OrderResponse(
                    order_id="IB_1001",
                    status=OrderStatus.FILLED,
                    symbol="AAPL",
                    quantity=100,
                    filled_quantity=100,
                    average_fill_price=Decimal("179.50"),
                    timestamp=datetime.now() - timedelta(hours=2),
                    commission=Decimal("1.00")
                ),
                OrderResponse(
                    order_id="IB_1002",
                    status=OrderStatus.CANCELLED,
                    symbol="TSLA",
                    quantity=50,
                    filled_quantity=0,
                    average_fill_price=None,
                    timestamp=datetime.now() - timedelta(hours=1),
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
            
            # Mock options chain - real implementation would call IB API
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
            
            # Generate mock options data
            for strike in chain['strikes']:
                for exp_date in chain['expiration_dates']:
                    call_key = f"{underlying_symbol}_{exp_date}_{strike}_C"
                    put_key = f"{underlying_symbol}_{exp_date}_{strike}_P"
                    
                    chain['calls'][call_key] = {
                        'symbol': call_key,
                        'strike': strike,
                        'expiration': exp_date,
                        'bid': max(0.1, 180 - strike + 2),
                        'ask': max(0.2, 180 - strike + 2.1),
                        'last': max(0.15, 180 - strike + 2.05),
                        'volume': 100,
                        'open_interest': 500,
                        'delta': 0.5,
                        'gamma': 0.01,
                        'theta': -0.05,
                        'vega': 0.15,
                        'iv': 0.25
                    }
                    
                    chain['puts'][put_key] = {
                        'symbol': put_key,
                        'strike': strike,
                        'expiration': exp_date,
                        'bid': max(0.1, strike - 180 + 2),
                        'ask': max(0.2, strike - 180 + 2.1),
                        'last': max(0.15, strike - 180 + 2.05),
                        'volume': 80,
                        'open_interest': 300,
                        'delta': -0.5,
                        'gamma': 0.01,
                        'theta': -0.05,
                        'vega': 0.15,
                        'iv': 0.25
                    }
            
            return chain
            
        except Exception as e:
            self._handle_error(e, f"Get options chain for {underlying_symbol} failed")
            raise MarketDataError(f"Failed to get options chain for {underlying_symbol}: {str(e)}", self.broker_name)
    
    async def get_option_quote(self, option_symbol: str) -> Quote:
        """Get option quote"""
        try:
            # Mock option quote - real implementation would call IB API
            return Quote(
                symbol=option_symbol,
                bid=Decimal("2.45"),
                ask=Decimal("2.55"),
                last=Decimal("2.50"),
                volume=150,
                timestamp=datetime.now(),
                bid_size=10,
                ask_size=15
            )
            
        except Exception as e:
            self._handle_error(e, f"Get option quote for {option_symbol} failed")
            raise MarketDataError(f"Failed to get option quote for {option_symbol}: {str(e)}", self.broker_name)
    
    async def get_portfolio_performance(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get portfolio performance metrics"""
        try:
            # Mock portfolio performance - real implementation would call IB API
            return {
                'total_return': 0.12,
                'total_return_pct': 12.0,
                'sharpe_ratio': 1.25,
                'max_drawdown': -0.08,
                'volatility': 0.15,
                'beta': 1.05,
                'alpha': 0.02,
                'start_value': 100000.0,
                'end_value': 112000.0,
                'benchmark_return': 0.10
            }
            
        except Exception as e:
            self._handle_error(e, "Get portfolio performance failed")
            return {}
    
    def _convert_to_ib_order(self, order: OrderRequest) -> Dict[str, Any]:
        """Convert OrderRequest to IB order format"""
        ib_order = {
            'symbol': order.symbol,
            'quantity': order.quantity,
            'action': 'BUY' if order.side in [OrderSide.BUY, OrderSide.BUY_TO_COVER] else 'SELL',
            'orderType': self._convert_order_type(order.order_type),
            'timeInForce': order.time_in_force
        }
        
        if order.price:
            ib_order['lmtPrice'] = float(order.price)
        
        if order.stop_price:
            ib_order['auxPrice'] = float(order.stop_price)
        
        return ib_order
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert OrderType to IB order type"""
        mapping = {
            OrderType.MARKET: 'MKT',
            OrderType.LIMIT: 'LMT',
            OrderType.STOP: 'STP',
            OrderType.STOP_LIMIT: 'STP LMT',
            OrderType.TRAILING_STOP: 'TRAIL'
        }
        return mapping.get(order_type, 'MKT')