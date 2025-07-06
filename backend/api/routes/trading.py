from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from services.database import get_db
from services.order_execution import order_execution_engine
from services.risk_management import risk_manager
from services.broker_service import trading_service, BrokerType
from models.trade import Order, Trade, Position, OrderSide, OrderType, OrderStatus
from models.broker import BrokerAccount
from models.user import User
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class OrderRequest(BaseModel):
    symbol: str
    quantity: int
    side: str  # buy/sell
    order_type: str  # market/limit/stop/stop_limit
    time_in_force: str = "day"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    broker_account_id: str
    
    @validator('side')
    def validate_side(cls, v):
        if v not in ['buy', 'sell']:
            raise ValueError('Side must be buy or sell')
        return v
    
    @validator('order_type')
    def validate_order_type(cls, v):
        if v not in ['market', 'limit', 'stop', 'stop_limit']:
            raise ValueError('Invalid order type')
        return v
    
    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class OrderResponse(BaseModel):
    order_id: str
    symbol: str
    quantity: int
    side: str
    order_type: str
    status: str
    limit_price: Optional[float]
    stop_price: Optional[float]
    filled_quantity: int
    filled_price: Optional[float]
    submitted_at: Optional[str]
    filled_at: Optional[str]
    estimated_cost: float

class PositionResponse(BaseModel):
    symbol: str
    quantity: float
    side: str
    avg_cost: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    day_pnl: float
    last_price: float

@router.post("/orders", response_model=Dict[str, Any])
async def place_order(
    order_request: OrderRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Place a trading order"""
    try:
        user_id = current_user.get("sub")
        
        # Validate broker account belongs to user
        result = await db.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.id == order_request.broker_account_id,
                    BrokerAccount.user_id == user_id
                )
            )
        )
        broker_account = result.scalar_one_or_none()
        
        if not broker_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker account not found"
            )
        
        # Prepare order data
        order_data = {
            "symbol": order_request.symbol.upper(),
            "quantity": order_request.quantity,
            "side": order_request.side,
            "order_type": order_request.order_type,
            "time_in_force": order_request.time_in_force,
            "limit_price": order_request.limit_price,
            "stop_price": order_request.stop_price,
            "price": order_request.limit_price or 0  # For risk calculations
        }
        
        # Submit order for execution
        order_id = await order_execution_engine.submit_order(
            user_id, order_request.broker_account_id, order_data, db
        )
        
        # Start execution engine if not running
        background_tasks.add_task(order_execution_engine.start)
        
        logger.info(f"Order placed successfully: {order_id}")
        
        return {
            "order_id": order_id,
            "status": "submitted",
            "message": "Order submitted for execution",
            "symbol": order_request.symbol,
            "quantity": order_request.quantity,
            "side": order_request.side
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to place order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to place order"
        )

@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Get user's orders"""
    try:
        user_id = current_user.get("sub")
        
        query = select(Order).where(Order.user_id == user_id)
        
        if status_filter:
            query = query.where(Order.status == OrderStatus(status_filter))
        
        query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        return [
            OrderResponse(
                order_id=str(order.id),
                symbol=order.symbol,
                quantity=order.quantity,
                side=order.side.value,
                order_type=order.order_type.value,
                status=order.status.value,
                limit_price=order.limit_price,
                stop_price=order.stop_price,
                filled_quantity=order.filled_quantity,
                filled_price=order.filled_price,
                submitted_at=order.submitted_at.isoformat() if order.submitted_at else None,
                filled_at=order.filled_at.isoformat() if order.filled_at else None,
                estimated_cost=order.estimated_cost or 0.0
            )
            for order in orders
        ]
        
    except Exception as e:
        logger.error(f"Failed to get orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orders"
        )

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Get specific order details"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(
            select(Order).where(
                and_(Order.id == order_id, Order.user_id == user_id)
            )
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return OrderResponse(
            order_id=str(order.id),
            symbol=order.symbol,
            quantity=order.quantity,
            side=order.side.value,
            order_type=order.order_type.value,
            status=order.status.value,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            filled_quantity=order.filled_quantity,
            filled_price=order.filled_price,
            submitted_at=order.submitted_at.isoformat() if order.submitted_at else None,
            filled_at=order.filled_at.isoformat() if order.filled_at else None,
            estimated_cost=order.estimated_cost or 0.0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order"
        )

@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Cancel an order"""
    try:
        user_id = current_user.get("sub")
        
        # Verify order belongs to user
        result = await db.execute(
            select(Order).where(
                and_(Order.id == order_id, Order.user_id == user_id)
            )
        )
        order = result.scalar_one_or_none()
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Cancel the order
        success = await order_execution_engine.cancel_order(order_id, db)
        
        if success:
            return {"message": "Order cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to cancel order"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order"
        )

@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Get user's positions"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(
            select(Position).where(Position.user_id == user_id)
        )
        positions = result.scalars().all()
        
        return [
            PositionResponse(
                symbol=pos.symbol,
                quantity=pos.quantity,
                side=pos.side.value,
                avg_cost=pos.avg_cost,
                market_value=pos.market_value,
                unrealized_pnl=pos.unrealized_pnl,
                unrealized_pnl_percent=pos.unrealized_pnl_percent,
                day_pnl=pos.day_pnl,
                last_price=pos.last_price
            )
            for pos in positions
        ]
        
    except Exception as e:
        logger.error(f"Failed to get positions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve positions"
        )

@router.get("/trades")
async def get_trades(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Get user's trade history"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(
            select(Trade)
            .where(Trade.user_id == user_id)
            .order_by(Trade.executed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        trades = result.scalars().all()
        
        return {
            "trades": [
                {
                    "trade_id": str(trade.id),
                    "symbol": trade.symbol,
                    "quantity": trade.quantity,
                    "side": trade.side.value,
                    "price": trade.price,
                    "trade_value": trade.trade_value,
                    "commission": trade.commission,
                    "executed_at": trade.executed_at.isoformat()
                }
                for trade in trades
            ],
            "total": len(trades)
        }
        
    except Exception as e:
        logger.error(f"Failed to get trades: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trades"
        )