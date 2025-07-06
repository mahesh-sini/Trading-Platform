from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import asyncio
from enum import Enum
import alpaca_trade_api as tradeapi
import yfinance as yf
import os

logger = logging.getLogger(__name__)

class BrokerType(Enum):
    ALPACA = "alpaca"
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"

@dataclass
class OrderRequest:
    symbol: str
    quantity: int
    side: str  # buy/sell
    order_type: str  # market/limit/stop
    time_in_force: str = "day"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
@dataclass
class OrderResponse:
    order_id: str
    status: str
    symbol: str
    quantity: int
    side: str
    filled_price: Optional[float] = None
    filled_quantity: int = 0
    submitted_at: Optional[datetime] = None
    
@dataclass
class Position:
    symbol: str
    quantity: float
    side: str
    avg_cost: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    
@dataclass
class AccountInfo:
    account_number: str
    buying_power: float
    cash: float
    portfolio_value: float
    day_trading_buying_power: float
    equity: float

class BrokerInterface(ABC):
    @abstractmethod
    async def connect(self, credentials: Dict[str, str]) -> bool:
        pass
    
    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        pass
    
    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> OrderResponse:
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        pass
    
    @abstractmethod
    async def get_orders(self, status: Optional[str] = None) -> List[OrderResponse]:
        pass

class AlpacaBroker(BrokerInterface):
    def __init__(self):
        self.api = None
        self.is_connected = False
        
    async def connect(self, credentials: Dict[str, str]) -> bool:
        try:
            api_key = credentials.get("api_key")
            api_secret = credentials.get("api_secret")
            base_url = credentials.get("base_url", "https://paper-api.alpaca.markets")
            
            self.api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
            
            # Test connection
            account = self.api.get_account()
            if account:
                self.is_connected = True
                logger.info("Successfully connected to Alpaca")
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {str(e)}")
            self.is_connected = False
            
        return False
    
    async def get_account_info(self) -> AccountInfo:
        if not self.is_connected:
            raise Exception("Not connected to broker")
            
        try:
            account = self.api.get_account()
            return AccountInfo(
                account_number=account.account_number,
                buying_power=float(account.buying_power),
                cash=float(account.cash),
                portfolio_value=float(account.portfolio_value),
                day_trading_buying_power=float(account.daytrading_buying_power),
                equity=float(account.equity)
            )
        except Exception as e:
            logger.error(f"Failed to get account info: {str(e)}")
            raise
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        if not self.is_connected:
            raise Exception("Not connected to broker")
            
        try:
            alpaca_order = self.api.submit_order(
                symbol=order.symbol,
                qty=order.quantity,
                side=order.side,
                type=order.order_type,
                time_in_force=order.time_in_force,
                limit_price=order.limit_price,
                stop_price=order.stop_price
            )
            
            return OrderResponse(
                order_id=alpaca_order.id,
                status=alpaca_order.status,
                symbol=alpaca_order.symbol,
                quantity=int(alpaca_order.qty),
                side=alpaca_order.side,
                submitted_at=alpaca_order.submitted_at
            )
            
        except Exception as e:
            logger.error(f"Failed to place order: {str(e)}")
            raise
    
    async def get_order(self, order_id: str) -> OrderResponse:
        if not self.is_connected:
            raise Exception("Not connected to broker")
            
        try:
            alpaca_order = self.api.get_order(order_id)
            
            return OrderResponse(
                order_id=alpaca_order.id,
                status=alpaca_order.status,
                symbol=alpaca_order.symbol,
                quantity=int(alpaca_order.qty),
                side=alpaca_order.side,
                filled_price=float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
                filled_quantity=int(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0,
                submitted_at=alpaca_order.submitted_at
            )
            
        except Exception as e:
            logger.error(f"Failed to get order: {str(e)}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        if not self.is_connected:
            raise Exception("Not connected to broker")
            
        try:
            self.api.cancel_order(order_id)
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            return False
    
    async def get_positions(self) -> List[Position]:
        if not self.is_connected:
            raise Exception("Not connected to broker")
            
        try:
            positions = self.api.list_positions()
            result = []
            
            for pos in positions:
                result.append(Position(
                    symbol=pos.symbol,
                    quantity=float(pos.qty),
                    side=pos.side,
                    avg_cost=float(pos.avg_cost),
                    market_value=float(pos.market_value),
                    unrealized_pnl=float(pos.unrealized_pl),
                    unrealized_pnl_percent=float(pos.unrealized_plpc)
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            raise
    
    async def get_orders(self, status: Optional[str] = None) -> List[OrderResponse]:
        if not self.is_connected:
            raise Exception("Not connected to broker")
            
        try:
            orders = self.api.list_orders(status=status)
            result = []
            
            for order in orders:
                result.append(OrderResponse(
                    order_id=order.id,
                    status=order.status,
                    symbol=order.symbol,
                    quantity=int(order.qty),
                    side=order.side,
                    filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                    filled_quantity=int(order.filled_qty) if order.filled_qty else 0,
                    submitted_at=order.submitted_at
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            raise

class BrokerFactory:
    @staticmethod
    def create_broker(broker_type: BrokerType) -> BrokerInterface:
        if broker_type == BrokerType.ALPACA:
            return AlpacaBroker()
        # Add other brokers here
        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")

class TradingService:
    def __init__(self):
        self.brokers: Dict[str, BrokerInterface] = {}
        
    async def add_broker_connection(self, broker_id: str, broker_type: BrokerType, credentials: Dict[str, str]) -> bool:
        try:
            broker = BrokerFactory.create_broker(broker_type)
            success = await broker.connect(credentials)
            
            if success:
                self.brokers[broker_id] = broker
                logger.info(f"Added broker connection: {broker_id}")
                return True
            else:
                logger.error(f"Failed to connect to broker: {broker_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding broker connection: {str(e)}")
            return False
    
    async def remove_broker_connection(self, broker_id: str):
        if broker_id in self.brokers:
            del self.brokers[broker_id]
            logger.info(f"Removed broker connection: {broker_id}")
    
    async def get_account_info(self, broker_id: str) -> AccountInfo:
        if broker_id not in self.brokers:
            raise Exception(f"Broker not found: {broker_id}")
        
        return await self.brokers[broker_id].get_account_info()
    
    async def place_order(self, broker_id: str, order: OrderRequest) -> OrderResponse:
        if broker_id not in self.brokers:
            raise Exception(f"Broker not found: {broker_id}")
        
        # Add risk management checks here
        await self._validate_order(order)
        
        return await self.brokers[broker_id].place_order(order)
    
    async def get_order(self, broker_id: str, order_id: str) -> OrderResponse:
        if broker_id not in self.brokers:
            raise Exception(f"Broker not found: {broker_id}")
        
        return await self.brokers[broker_id].get_order(order_id)
    
    async def cancel_order(self, broker_id: str, order_id: str) -> bool:
        if broker_id not in self.brokers:
            raise Exception(f"Broker not found: {broker_id}")
        
        return await self.brokers[broker_id].cancel_order(order_id)
    
    async def get_positions(self, broker_id: str) -> List[Position]:
        if broker_id not in self.brokers:
            raise Exception(f"Broker not found: {broker_id}")
        
        return await self.brokers[broker_id].get_positions()
    
    async def get_orders(self, broker_id: str, status: Optional[str] = None) -> List[OrderResponse]:
        if broker_id not in self.brokers:
            raise Exception(f"Broker not found: {broker_id}")
        
        return await self.brokers[broker_id].get_orders(status)
    
    async def _validate_order(self, order: OrderRequest):
        """Risk management and order validation"""
        # Basic validation
        if order.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if order.order_type == "limit" and not order.limit_price:
            raise ValueError("Limit price required for limit orders")
        
        if order.order_type in ["stop", "stop_limit"] and not order.stop_price:
            raise ValueError("Stop price required for stop orders")
        
        # Add more sophisticated risk checks here
        # - Position size limits
        # - Daily loss limits
        # - Correlation checks
        # - Volatility checks
        
    async def test_broker_connection(self, broker_type: BrokerType, credentials: Dict[str, str]) -> bool:
        """Test broker connection without storing it"""
        try:
            broker = BrokerFactory.create_broker(broker_type)
            return await broker.connect(credentials)
        except Exception as e:
            logger.error(f"Broker connection test failed: {str(e)}")
            return False

# Singleton instance
trading_service = TradingService()