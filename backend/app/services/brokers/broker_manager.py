"""
Unified Broker Manager - Abstraction layer for all broker integrations
"""

import asyncio
from typing import Dict, List, Optional, Any, Type, Union
from datetime import datetime
from decimal import Decimal
import logging
from enum import Enum

from .base_broker import (
    BaseBroker, BrokerCredentials, Quote, Position, OrderRequest, OrderResponse, 
    AccountInfo, HistoricalBar, OrderType, OrderSide, OrderStatus, AssetType,
    BrokerException, ConnectionError, AuthenticationError, OrderError, MarketDataError
)
from .interactive_brokers import InteractiveBrokersBroker
from .td_ameritrade import TDAmeritradeBroker
from .etrade import EtradeBroker
# Indian Brokers
from .zerodha_kite import ZerodhaKiteBroker
from .icici_breeze import ICICIBreezeBroker
from .upstox import UpstoxBroker
from .angel_one import AngelOneBroker

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """Supported broker types"""
    # US Brokers
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    ETRADE = "etrade"
    ALPACA = "alpaca"  # Future implementation
    SCHWAB = "schwab"  # Future implementation
    
    # Indian Brokers
    ZERODHA_KITE = "zerodha_kite"
    ICICI_BREEZE = "icici_breeze"
    UPSTOX = "upstox"
    ANGEL_ONE = "angel_one"


class BrokerManager:
    """Unified broker management and routing"""
    
    def __init__(self):
        self.brokers: Dict[str, BaseBroker] = {}
        self.default_broker: Optional[str] = None
        self.broker_configs: Dict[str, Dict[str, Any]] = {}
        
        # Broker class registry
        self.broker_registry: Dict[BrokerType, Type[BaseBroker]] = {
            # US Brokers
            BrokerType.INTERACTIVE_BROKERS: InteractiveBrokersBroker,
            BrokerType.TD_AMERITRADE: TDAmeritradeBroker,
            BrokerType.ETRADE: EtradeBroker,
            
            # Indian Brokers
            BrokerType.ZERODHA_KITE: ZerodhaKiteBroker,
            BrokerType.ICICI_BREEZE: ICICIBreezeBroker,
            BrokerType.UPSTOX: UpstoxBroker,
            BrokerType.ANGEL_ONE: AngelOneBroker
        }
    
    async def add_broker(
        self, 
        broker_id: str, 
        broker_type: BrokerType, 
        credentials: BrokerCredentials,
        make_default: bool = False
    ) -> bool:
        """Add a broker connection"""
        try:
            if broker_type not in self.broker_registry:
                raise BrokerException(f"Unsupported broker type: {broker_type}")
            
            broker_class = self.broker_registry[broker_type]
            broker = broker_class(credentials)
            
            # Test connection
            await broker.connect()
            
            self.brokers[broker_id] = broker
            self.broker_configs[broker_id] = {
                'type': broker_type,
                'credentials': credentials,
                'connected_at': datetime.now(),
                'status': 'connected'
            }
            
            if make_default or not self.default_broker:
                self.default_broker = broker_id
            
            logger.info(f"Added broker {broker_id} ({broker_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add broker {broker_id}: {str(e)}")
            raise BrokerException(f"Failed to add broker: {str(e)}")
    
    async def remove_broker(self, broker_id: str) -> bool:
        """Remove a broker connection"""
        try:
            if broker_id in self.brokers:
                await self.brokers[broker_id].disconnect()
                del self.brokers[broker_id]
                del self.broker_configs[broker_id]
                
                if self.default_broker == broker_id:
                    self.default_broker = next(iter(self.brokers.keys())) if self.brokers else None
                
                logger.info(f"Removed broker {broker_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove broker {broker_id}: {str(e)}")
            return False
    
    def get_broker(self, broker_id: Optional[str] = None) -> BaseBroker:
        """Get broker instance"""
        broker_id = broker_id or self.default_broker
        
        if not broker_id or broker_id not in self.brokers:
            raise BrokerException(f"Broker not found: {broker_id}")
        
        return self.brokers[broker_id]
    
    def list_brokers(self) -> Dict[str, Dict[str, Any]]:
        """List all configured brokers"""
        return {
            broker_id: {
                **config,
                'is_connected': broker.is_connected,
                'is_default': broker_id == self.default_broker
            }
            for broker_id, config in self.broker_configs.items()
            for broker in [self.brokers[broker_id]]
        }
    
    async def set_default_broker(self, broker_id: str) -> bool:
        """Set default broker"""
        if broker_id in self.brokers:
            self.default_broker = broker_id
            logger.info(f"Set default broker to {broker_id}")
            return True
        return False
    
    # Unified broker operations
    
    async def get_account_info(self, broker_id: Optional[str] = None) -> AccountInfo:
        """Get account information from specified or default broker"""
        broker = self.get_broker(broker_id)
        return await broker.get_account_info()
    
    async def get_all_accounts_info(self) -> Dict[str, AccountInfo]:
        """Get account information from all connected brokers"""
        accounts = {}
        for broker_id, broker in self.brokers.items():
            try:
                accounts[broker_id] = await broker.get_account_info()
            except Exception as e:
                logger.error(f"Failed to get account info from {broker_id}: {str(e)}")
                
        return accounts
    
    async def get_positions(self, broker_id: Optional[str] = None) -> List[Position]:
        """Get positions from specified or default broker"""
        broker = self.get_broker(broker_id)
        return await broker.get_positions()
    
    async def get_all_positions(self) -> Dict[str, List[Position]]:
        """Get positions from all connected brokers"""
        all_positions = {}
        for broker_id, broker in self.brokers.items():
            try:
                all_positions[broker_id] = await broker.get_positions()
            except Exception as e:
                logger.error(f"Failed to get positions from {broker_id}: {str(e)}")
                
        return all_positions
    
    async def get_consolidated_positions(self) -> List[Position]:
        """Get consolidated positions across all brokers"""
        all_positions = await self.get_all_positions()
        consolidated = {}
        
        for broker_id, positions in all_positions.items():
            for position in positions:
                symbol = position.symbol
                
                if symbol in consolidated:
                    # Consolidate position
                    existing = consolidated[symbol]
                    total_quantity = existing.quantity + position.quantity
                    
                    if total_quantity != 0:
                        # Weighted average price
                        total_cost = (existing.quantity * existing.average_price + 
                                    position.quantity * position.average_price)
                        avg_price = total_cost / total_quantity
                        
                        consolidated[symbol] = Position(
                            symbol=symbol,
                            quantity=total_quantity,
                            average_price=avg_price,
                            current_price=position.current_price,  # Use latest price
                            market_value=(existing.market_value or 0) + (position.market_value or 0),
                            unrealized_pnl=(existing.unrealized_pnl or 0) + (position.unrealized_pnl or 0),
                            asset_type=position.asset_type,
                            side="long" if total_quantity > 0 else "short"
                        )
                    else:
                        # Net position is zero, remove from consolidated
                        del consolidated[symbol]
                else:
                    consolidated[symbol] = position
        
        return list(consolidated.values())
    
    async def get_quote(self, symbol: str, broker_id: Optional[str] = None) -> Quote:
        """Get quote from specified or default broker"""
        broker = self.get_broker(broker_id)
        return await broker.get_quote(symbol)
    
    async def get_best_quote(self, symbol: str) -> Quote:
        """Get best quote across all brokers"""
        quotes = {}
        
        # Get quotes from all brokers
        for broker_id, broker in self.brokers.items():
            try:
                quotes[broker_id] = await broker.get_quote(symbol)
            except Exception as e:
                logger.warning(f"Failed to get quote from {broker_id}: {str(e)}")
        
        if not quotes:
            raise MarketDataError(f"No quotes available for {symbol}")
        
        # Find best bid (highest) and best ask (lowest)
        best_bid = None
        best_ask = None
        latest_quote = None
        
        for quote in quotes.values():
            if quote.bid and (not best_bid or quote.bid > best_bid):
                best_bid = quote.bid
            
            if quote.ask and (not best_ask or quote.ask < best_ask):
                best_ask = quote.ask
            
            # Use most recent quote as base
            if not latest_quote or quote.timestamp > latest_quote.timestamp:
                latest_quote = quote
        
        # Create consolidated quote
        return Quote(
            symbol=symbol,
            bid=best_bid,
            ask=best_ask,
            last=latest_quote.last,
            volume=latest_quote.volume,
            timestamp=datetime.now(),
            bid_size=latest_quote.bid_size,
            ask_size=latest_quote.ask_size,
            high=latest_quote.high,
            low=latest_quote.low,
            open=latest_quote.open,
            close=latest_quote.close
        )
    
    async def place_order(
        self, 
        order: OrderRequest, 
        broker_id: Optional[str] = None
    ) -> OrderResponse:
        """Place order with specified or default broker"""
        broker = self.get_broker(broker_id)
        return await broker.place_order(order)
    
    async def smart_order_routing(self, order: OrderRequest) -> OrderResponse:
        """Smart order routing across brokers for best execution"""
        try:
            # Get quotes from all brokers
            symbol = order.symbol
            quotes = {}
            
            for broker_id, broker in self.brokers.items():
                try:
                    quotes[broker_id] = await broker.get_quote(symbol)
                except Exception:
                    continue
            
            if not quotes:
                # Fallback to default broker
                return await self.place_order(order)
            
            # Find best broker based on order type and side
            best_broker_id = None
            
            if order.order_type == OrderType.MARKET:
                if order.side in [OrderSide.BUY, OrderSide.BUY_TO_COVER]:
                    # Buy orders want lowest ask
                    best_ask = None
                    for broker_id, quote in quotes.items():
                        if quote.ask and (not best_ask or quote.ask < best_ask):
                            best_ask = quote.ask
                            best_broker_id = broker_id
                else:
                    # Sell orders want highest bid
                    best_bid = None
                    for broker_id, quote in quotes.items():
                        if quote.bid and (not best_bid or quote.bid > best_bid):
                            best_bid = quote.bid
                            best_broker_id = broker_id
            
            # Use best broker or fallback to default
            broker_id = best_broker_id or self.default_broker
            return await self.place_order(order, broker_id)
            
        except Exception as e:
            logger.error(f"Smart order routing failed: {str(e)}")
            # Fallback to default broker
            return await self.place_order(order)
    
    async def cancel_order(
        self, 
        order_id: str, 
        broker_id: Optional[str] = None
    ) -> bool:
        """Cancel order"""
        broker = self.get_broker(broker_id)
        return await broker.cancel_order(order_id)
    
    async def get_order_status(
        self, 
        order_id: str, 
        broker_id: Optional[str] = None
    ) -> OrderResponse:
        """Get order status"""
        broker = self.get_broker(broker_id)
        return await broker.get_order_status(order_id)
    
    async def get_orders(
        self, 
        broker_id: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[OrderResponse]:
        """Get orders from specified or default broker"""
        broker = self.get_broker(broker_id)
        return await broker.get_orders(status, start_date, end_date)
    
    async def get_all_orders(
        self,
        status: Optional[OrderStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, List[OrderResponse]]:
        """Get orders from all brokers"""
        all_orders = {}
        
        for broker_id, broker in self.brokers.items():
            try:
                all_orders[broker_id] = await broker.get_orders(status, start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to get orders from {broker_id}: {str(e)}")
                
        return all_orders
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
        broker_id: Optional[str] = None
    ) -> List[HistoricalBar]:
        """Get historical data"""
        broker = self.get_broker(broker_id)
        return await broker.get_historical_data(symbol, period, start_date, end_date, limit)
    
    async def get_options_chain(
        self, 
        underlying_symbol: str,
        expiration_date: Optional[datetime] = None,
        broker_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get options chain"""
        broker = self.get_broker(broker_id)
        return await broker.get_options_chain(underlying_symbol, expiration_date)
    
    async def is_market_open(self, broker_id: Optional[str] = None) -> bool:
        """Check if market is open"""
        broker = self.get_broker(broker_id)
        return await broker.is_market_open()
    
    async def health_check(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all broker connections"""
        health_status = {}
        
        for broker_id, broker in self.brokers.items():
            try:
                # Test basic connectivity
                is_connected = broker.is_connected
                market_open = await broker.is_market_open()
                
                health_status[broker_id] = {
                    'status': 'healthy',
                    'connected': is_connected,
                    'market_open': market_open,
                    'broker_name': broker.broker_name,
                    'last_error': broker.last_error,
                    'supported_assets': [asset.value for asset in broker.supported_asset_types],
                    'supported_orders': [order.value for order in broker.supported_order_types]
                }
                
            except Exception as e:
                health_status[broker_id] = {
                    'status': 'error',
                    'connected': False,
                    'error': str(e),
                    'broker_name': getattr(broker, 'broker_name', 'Unknown')
                }
        
        return health_status
    
    async def disconnect_all(self) -> bool:
        """Disconnect from all brokers"""
        success = True
        
        for broker_id, broker in self.brokers.items():
            try:
                await broker.disconnect()
                logger.info(f"Disconnected from {broker_id}")
            except Exception as e:
                logger.error(f"Failed to disconnect from {broker_id}: {str(e)}")
                success = False
        
        return success
    
    def get_broker_capabilities(self, broker_id: Optional[str] = None) -> Dict[str, Any]:
        """Get broker capabilities"""
        broker = self.get_broker(broker_id)
        
        return {
            'broker_name': broker.broker_name,
            'supported_asset_types': [asset.value for asset in broker.supported_asset_types],
            'supported_order_types': [order.value for order in broker.supported_order_types],
            'supports_options': AssetType.OPTION in broker.supported_asset_types,
            'supports_forex': AssetType.FOREX in broker.supported_asset_types,
            'supports_crypto': AssetType.CRYPTO in broker.supported_asset_types
        }


# Global broker manager instance
broker_manager = BrokerManager()