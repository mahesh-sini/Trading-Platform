"""
Base Broker Interface - Abstract class for all broker integrations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"
    BUY_TO_COVER = "buy_to_cover"
    SELL_SHORT = "sell_short"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class AssetType(Enum):
    STOCK = "stock"
    OPTION = "option"
    ETF = "etf"
    MUTUAL_FUND = "mutual_fund"
    BOND = "bond"
    CRYPTO = "crypto"
    FOREX = "forex"

@dataclass
class BrokerCredentials:
    """Broker authentication credentials"""
    api_key: str
    secret_key: str
    account_id: Optional[str] = None
    sandbox: bool = True
    additional_params: Optional[Dict[str, Any]] = None

@dataclass
class Quote:
    """Market quote data"""
    symbol: str
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    last: Optional[Decimal]
    volume: Optional[int]
    timestamp: datetime
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None
    close: Optional[Decimal] = None

@dataclass
class Position:
    """Account position"""
    symbol: str
    quantity: Decimal
    average_price: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    asset_type: AssetType
    side: str  # "long" or "short"

@dataclass
class OrderRequest:
    """Order placement request"""
    symbol: str
    quantity: int
    side: OrderSide
    order_type: OrderType
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = "DAY"
    asset_type: AssetType = AssetType.STOCK

@dataclass
class OrderResponse:
    """Order response from broker"""
    order_id: str
    status: OrderStatus
    symbol: str
    quantity: int
    filled_quantity: int
    average_fill_price: Optional[Decimal]
    timestamp: datetime
    commission: Optional[Decimal] = None
    error_message: Optional[str] = None

@dataclass
class AccountInfo:
    """Account information"""
    account_id: str
    buying_power: Decimal
    cash: Decimal
    equity: Decimal
    day_trading_buying_power: Optional[Decimal]
    maintenance_margin: Optional[Decimal]
    currency: str = "USD"

@dataclass
class HistoricalBar:
    """Historical price bar"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class BaseBroker(ABC):
    """Abstract base class for all broker implementations"""
    
    def __init__(self, credentials: BrokerCredentials):
        self.credentials = credentials
        self.is_connected = False
        self.last_error = None
    
    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return the broker name"""
        pass
    
    @property
    @abstractmethod
    def supported_asset_types(self) -> List[AssetType]:
        """Return list of supported asset types"""
        pass
    
    @property
    @abstractmethod
    def supported_order_types(self) -> List[OrderType]:
        """Return list of supported order types"""
        pass
    
    # Connection Management
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker API"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from broker API"""
        pass
    
    @abstractmethod
    async def is_market_open(self) -> bool:
        """Check if market is currently open"""
        pass
    
    # Account Information
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get account information"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all account positions"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for specific symbol"""
        pass
    
    # Market Data
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Get current quote for symbol"""
        pass
    
    @abstractmethod
    async def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[HistoricalBar]:
        """Get historical price data"""
        pass
    
    # Order Management
    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place a trading order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResponse:
        """Get status of an order"""
        pass
    
    @abstractmethod
    async def get_orders(
        self, 
        status: Optional[OrderStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[OrderResponse]:
        """Get order history"""
        pass
    
    # Options-specific methods (optional)
    async def get_options_chain(
        self, 
        underlying_symbol: str,
        expiration_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get options chain - override if broker supports options"""
        raise NotImplementedError(f"{self.broker_name} does not support options trading")
    
    async def get_option_quote(self, option_symbol: str) -> Quote:
        """Get option quote - override if broker supports options"""
        raise NotImplementedError(f"{self.broker_name} does not support options trading")
    
    # Portfolio analysis (optional)
    async def get_portfolio_performance(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get portfolio performance metrics"""
        return {}
    
    # Utility methods
    def _handle_error(self, error: Exception, context: str = ""):
        """Handle and log errors"""
        self.last_error = f"{context}: {str(error)}"
        print(f"Broker Error [{self.broker_name}] {self.last_error}")
    
    def _validate_symbol(self, symbol: str) -> str:
        """Validate and normalize symbol format"""
        return symbol.upper().strip()
    
    def _validate_order_request(self, order: OrderRequest) -> bool:
        """Validate order request"""
        if not order.symbol:
            raise ValueError("Symbol is required")
        
        if order.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not order.price:
            raise ValueError("Price is required for limit orders")
        
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not order.stop_price:
            raise ValueError("Stop price is required for stop orders")
        
        if order.asset_type not in self.supported_asset_types:
            raise ValueError(f"Asset type {order.asset_type} not supported by {self.broker_name}")
        
        if order.order_type not in self.supported_order_types:
            raise ValueError(f"Order type {order.order_type} not supported by {self.broker_name}")
        
        return True


class BrokerException(Exception):
    """Base exception for broker-related errors"""
    
    def __init__(self, message: str, broker_name: str = "", error_code: str = ""):
        self.broker_name = broker_name
        self.error_code = error_code
        super().__init__(message)


class ConnectionError(BrokerException):
    """Connection-related errors"""
    pass


class AuthenticationError(BrokerException):
    """Authentication-related errors"""
    pass


class OrderError(BrokerException):
    """Order-related errors"""
    pass


class MarketDataError(BrokerException):
    """Market data-related errors"""
    pass


class RateLimitError(BrokerException):
    """Rate limiting errors"""
    pass