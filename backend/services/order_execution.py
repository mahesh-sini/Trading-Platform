from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import logging
from enum import Enum
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.trade import Order, Trade, OrderStatus, OrderSide, OrderType
from models.broker import BrokerAccount
from services.broker_service import trading_service, OrderRequest, OrderResponse
from services.risk_management import risk_manager

logger = logging.getLogger(__name__)

class ExecutionStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class ExecutionReport:
    order_id: str
    status: ExecutionStatus
    filled_quantity: int
    avg_fill_price: float
    total_cost: float
    commission: float
    timestamp: datetime
    broker_order_id: Optional[str] = None
    rejection_reason: Optional[str] = None

class OrderExecutionEngine:
    def __init__(self):
        self.pending_orders: Dict[str, Dict] = {}
        self.execution_queue = asyncio.Queue()
        self.is_running = False
        
    async def start(self):
        """Start the order execution engine"""
        if not self.is_running:
            self.is_running = True
            asyncio.create_task(self._execution_worker())
            logger.info("Order execution engine started")
    
    async def stop(self):
        """Stop the order execution engine"""
        self.is_running = False
        logger.info("Order execution engine stopped")
    
    async def submit_order(
        self,
        user_id: str,
        broker_account_id: str,
        order_data: Dict[str, Any],
        db: AsyncSession
    ) -> str:
        """Submit an order for execution"""
        
        try:
            # Generate order ID
            order_id = str(uuid.uuid4())
            
            # Get broker account
            result = await db.execute(
                select(BrokerAccount).where(BrokerAccount.id == broker_account_id)
            )
            broker_account = result.scalar_one_or_none()
            
            if not broker_account:
                raise ValueError("Broker account not found")
            
            # Risk management validation
            portfolio_data = await self._get_portfolio_data(user_id, db)
            user_settings = await self._get_user_settings(user_id, db)
            
            is_valid, errors = await risk_manager.validate_order(
                order_data, user_settings, portfolio_data
            )
            
            if not is_valid:
                raise ValueError(f"Risk management check failed: {', '.join(errors)}")
            
            # Create order in database
            order = Order(
                id=order_id,
                user_id=user_id,
                broker_account_id=broker_account_id,
                symbol=order_data["symbol"],
                quantity=order_data["quantity"],
                side=OrderSide(order_data["side"]),
                order_type=OrderType(order_data["order_type"]),
                time_in_force=order_data.get("time_in_force", "day"),
                limit_price=order_data.get("limit_price"),
                stop_price=order_data.get("stop_price"),
                status=OrderStatus.PENDING,
                estimated_cost=order_data["quantity"] * order_data.get("price", 0)
            )
            
            db.add(order)
            await db.commit()
            
            # Add to execution queue
            execution_data = {
                "order_id": order_id,
                "broker_account": broker_account,
                "order_data": order_data,
                "db_session": db
            }
            
            await self.execution_queue.put(execution_data)
            
            logger.info(f"Order submitted for execution: {order_id}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to submit order: {str(e)}")
            await db.rollback()
            raise
    
    async def cancel_order(self, order_id: str, db: AsyncSession) -> bool:
        """Cancel an order"""
        try:
            # Get order from database
            result = await db.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            
            if not order:
                raise ValueError("Order not found")
            
            # Check if order can be cancelled
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                raise ValueError(f"Cannot cancel order with status: {order.status}")
            
            # Cancel with broker if submitted
            if order.broker_order_id and order.status == OrderStatus.SUBMITTED:
                broker_success = await trading_service.cancel_order(
                    str(order.broker_account_id), order.broker_order_id
                )
                
                if not broker_success:
                    logger.warning(f"Failed to cancel order with broker: {order_id}")
            
            # Update order status
            order.status = OrderStatus.CANCELLED
            await db.commit()
            
            # Remove from pending orders if present
            if order_id in self.pending_orders:
                del self.pending_orders[order_id]
            
            logger.info(f"Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {str(e)}")
            await db.rollback()
            return False
    
    async def get_order_status(self, order_id: str, db: AsyncSession) -> Dict[str, Any]:
        """Get current order status"""
        try:
            result = await db.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            
            if not order:
                raise ValueError("Order not found")
            
            return {
                "order_id": str(order.id),
                "status": order.status.value,
                "symbol": order.symbol,
                "quantity": order.quantity,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "filled_quantity": order.filled_quantity,
                "filled_price": order.filled_price,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get order status: {str(e)}")
            raise
    
    async def _execution_worker(self):
        """Background worker for order execution"""
        while self.is_running:
            try:
                # Get next order from queue with timeout
                execution_data = await asyncio.wait_for(
                    self.execution_queue.get(), timeout=1.0
                )
                
                await self._execute_order(execution_data)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in execution worker: {str(e)}")
    
    async def _execute_order(self, execution_data: Dict):
        """Execute a single order"""
        order_id = execution_data["order_id"]
        broker_account = execution_data["broker_account"]
        order_data = execution_data["order_data"]
        db = execution_data["db_session"]
        
        try:
            # Create broker order request
            broker_order = OrderRequest(
                symbol=order_data["symbol"],
                quantity=order_data["quantity"],
                side=order_data["side"],
                order_type=order_data["order_type"],
                time_in_force=order_data.get("time_in_force", "day"),
                limit_price=order_data.get("limit_price"),
                stop_price=order_data.get("stop_price")
            )
            
            # Submit to broker
            broker_response = await trading_service.place_order(
                str(broker_account.id), broker_order
            )
            
            # Update order with broker response
            await db.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(
                    broker_order_id=broker_response.order_id,
                    status=OrderStatus.SUBMITTED,
                    submitted_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            # Add to pending orders for monitoring
            self.pending_orders[order_id] = {
                "broker_account_id": str(broker_account.id),
                "broker_order_id": broker_response.order_id,
                "submitted_at": datetime.utcnow()
            }
            
            logger.info(f"Order submitted to broker: {order_id} -> {broker_response.order_id}")
            
        except Exception as e:
            logger.error(f"Failed to execute order {order_id}: {str(e)}")
            
            # Update order status to rejected
            await db.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(
                    status=OrderStatus.REJECTED,
                    rejection_reason=str(e)
                )
            )
            await db.commit()
    
    async def monitor_orders(self, db: AsyncSession):
        """Monitor pending orders for fills and updates"""
        try:
            orders_to_remove = []
            
            for order_id, order_info in self.pending_orders.items():
                broker_account_id = order_info["broker_account_id"]
                broker_order_id = order_info["broker_order_id"]
                
                try:
                    # Get order status from broker
                    broker_order = await trading_service.get_order(
                        broker_account_id, broker_order_id
                    )
                    
                    # Update order in database based on broker status
                    updated = await self._update_order_from_broker(
                        order_id, broker_order, db
                    )
                    
                    # Remove from monitoring if filled, cancelled, or rejected
                    if broker_order.status in ["filled", "cancelled", "rejected"]:
                        orders_to_remove.append(order_id)
                        
                        # Create trade record if filled
                        if broker_order.status == "filled":
                            await self._create_trade_record(order_id, broker_order, db)
                    
                except Exception as e:
                    logger.error(f"Error monitoring order {order_id}: {str(e)}")
            
            # Remove completed orders from monitoring
            for order_id in orders_to_remove:
                del self.pending_orders[order_id]
                
        except Exception as e:
            logger.error(f"Error in order monitoring: {str(e)}")
    
    async def _update_order_from_broker(
        self, order_id: str, broker_order: OrderResponse, db: AsyncSession
    ) -> bool:
        """Update order status based on broker response"""
        try:
            status_mapping = {
                "pending": OrderStatus.PENDING,
                "submitted": OrderStatus.SUBMITTED,
                "partially_filled": OrderStatus.PARTIALLY_FILLED,
                "filled": OrderStatus.FILLED,
                "cancelled": OrderStatus.CANCELLED,
                "rejected": OrderStatus.REJECTED
            }
            
            status = status_mapping.get(broker_order.status, OrderStatus.PENDING)
            
            update_data = {
                "status": status,
                "filled_quantity": broker_order.filled_quantity
            }
            
            if broker_order.filled_price:
                update_data["filled_price"] = broker_order.filled_price
            
            if status == OrderStatus.FILLED:
                update_data["filled_at"] = datetime.utcnow()
            
            await db.execute(
                update(Order)
                .where(Order.id == order_id)
                .values(**update_data)
            )
            await db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update order from broker: {str(e)}")
            await db.rollback()
            return False
    
    async def _create_trade_record(
        self, order_id: str, broker_order: OrderResponse, db: AsyncSession
    ) -> bool:
        """Create trade record for filled orders"""
        try:
            # Get order details
            result = await db.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            
            if not order:
                logger.error(f"Order not found for trade creation: {order_id}")
                return False
            
            # Create trade record
            trade = Trade(
                user_id=order.user_id,
                broker_account_id=order.broker_account_id,
                order_id=order.id,
                strategy_id=order.strategy_id,
                broker_trade_id=broker_order.order_id,  # Using order ID as trade ID
                symbol=order.symbol,
                quantity=broker_order.filled_quantity,
                side=order.side,
                price=broker_order.filled_price,
                commission=0.0,  # TODO: Calculate actual commission
                trade_value=broker_order.filled_quantity * broker_order.filled_price,
                executed_at=datetime.utcnow()
            )
            
            db.add(trade)
            await db.commit()
            
            logger.info(f"Trade record created for order: {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create trade record: {str(e)}")
            await db.rollback()
            return False
    
    async def _get_portfolio_data(self, user_id: str, db: AsyncSession) -> Dict:
        """Get user portfolio data for risk management"""
        # TODO: Implement portfolio data retrieval
        return {
            "portfolio_value": 100000.0,  # Placeholder
            "buying_power": 50000.0,
            "daily_pnl": 0.0
        }
    
    async def _get_user_settings(self, user_id: str, db: AsyncSession) -> Dict:
        """Get user trading settings"""
        # TODO: Implement user settings retrieval
        return {
            "trading_enabled": True,
            "max_position_size": 0.10,
            "risk_tolerance": "medium"
        }

# Singleton instance
order_execution_engine = OrderExecutionEngine()