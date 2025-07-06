from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from services.database import get_db
from services.auth_service import get_current_user
from services.auto_trading_service import auto_trading_service
from models.user import User
from models.auto_trade import AutoTrade, AutoTradeStatus
from models.subscription import Subscription, SubscriptionStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Pydantic models
class AutoTradingSettings(BaseModel):
    enabled: bool
    mode: str = "conservative"  # conservative, moderate, aggressive
    
    @validator('mode')
    def validate_mode(cls, v):
        valid_modes = ["conservative", "moderate", "aggressive"]
        if v not in valid_modes:
            raise ValueError(f'Mode must be one of: {", ".join(valid_modes)}')
        return v

class AutoTradingStatusResponse(BaseModel):
    enabled: bool
    mode: str
    subscription_plan: str
    daily_limit: int
    trades_today: int
    remaining_trades: int
    successful_trades_today: int
    is_market_open: bool
    has_active_session: bool
    primary_broker_connected: bool

class AutoTradeResponse(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: int
    price: float
    executed_price: Optional[float]
    confidence: float
    expected_return: float
    status: str
    reason: str
    execution_time: Optional[datetime]
    realized_pnl: Optional[float]
    created_at: datetime

# Auto trading management endpoints
@router.get("/status", response_model=AutoTradingStatusResponse)
async def get_auto_trading_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current auto-trading status and statistics for the user"""
    try:
        status_data = await auto_trading_service.get_auto_trading_status(str(current_user.id))
        
        if "error" in status_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=status_data["error"]
            )
        
        return AutoTradingStatusResponse(
            enabled=status_data["enabled"],
            mode=current_user.auto_trading_mode,
            subscription_plan=status_data["subscription_plan"],
            daily_limit=status_data["daily_limit"],
            trades_today=status_data["trades_today"],
            remaining_trades=status_data["remaining_trades"],
            successful_trades_today=status_data["successful_trades_today"],
            is_market_open=status_data["is_market_open"],
            has_active_session=status_data["has_active_session"],
            primary_broker_connected=status_data["primary_broker_connected"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting auto-trading status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get auto-trading status"
        )

@router.post("/enable")
async def enable_auto_trading(
    settings: AutoTradingSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable auto-trading for the user"""
    try:
        # Check if user has a valid subscription for auto-trading
        result = await db.execute(
            select(Subscription)
            .join(Subscription.plan)
            .where(
                and_(
                    Subscription.user_id == current_user.id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription or not subscription.plan.automated_trading:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Auto-trading requires an active subscription with automated trading feature"
            )
        
        # Update user auto-trading settings
        current_user.auto_trading_enabled = settings.enabled
        current_user.auto_trading_mode = settings.mode
        await db.commit()
        
        # Enable auto-trading service
        if settings.enabled:
            success = await auto_trading_service.enable_auto_trading(str(current_user.id))
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to enable auto-trading. Please check your broker connection and subscription."
                )
        else:
            success = await auto_trading_service.disable_auto_trading(str(current_user.id))
        
        logger.info(f"Auto-trading {'enabled' if settings.enabled else 'disabled'} for user {current_user.email}")
        
        return {
            "message": f"Auto-trading {'enabled' if settings.enabled else 'disabled'} successfully",
            "enabled": settings.enabled,
            "mode": settings.mode
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling auto-trading: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update auto-trading settings"
        )

@router.post("/disable")
async def disable_auto_trading(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable auto-trading for the user"""
    try:
        # Update user settings
        current_user.auto_trading_enabled = False
        await db.commit()
        
        # Disable auto-trading service
        success = await auto_trading_service.disable_auto_trading(str(current_user.id))
        
        if not success:
            logger.warning(f"Failed to disable auto-trading service for user {current_user.id}")
        
        logger.info(f"Auto-trading disabled for user {current_user.email}")
        
        return {
            "message": "Auto-trading disabled successfully",
            "enabled": False
        }
        
    except Exception as e:
        logger.error(f"Error disabling auto-trading: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable auto-trading"
        )

@router.put("/settings")
async def update_auto_trading_settings(
    settings: AutoTradingSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update auto-trading settings"""
    try:
        # Update user settings
        current_user.auto_trading_enabled = settings.enabled
        current_user.auto_trading_mode = settings.mode
        await db.commit()
        
        # Update service settings if enabled
        if settings.enabled:
            success = await auto_trading_service.enable_auto_trading(str(current_user.id))
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to enable auto-trading. Please check your subscription and broker connection."
                )
        else:
            await auto_trading_service.disable_auto_trading(str(current_user.id))
        
        logger.info(f"Auto-trading settings updated for user {current_user.email}: {settings.dict()}")
        
        return {
            "message": "Auto-trading settings updated successfully",
            "enabled": settings.enabled,
            "mode": settings.mode
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating auto-trading settings: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update auto-trading settings"
        )

# Auto trading history and analytics
@router.get("/trades", response_model=List[AutoTradeResponse])
async def get_auto_trading_history(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    symbol: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get auto-trading history for the user"""
    try:
        # Build query
        query = select(AutoTrade).where(AutoTrade.user_id == current_user.id)
        
        # Apply filters
        if status_filter:
            try:
                status_enum = AutoTradeStatus(status_filter)
                query = query.where(AutoTrade.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status filter: {status_filter}"
                )
        
        if symbol:
            query = query.where(AutoTrade.symbol == symbol.upper())
        
        if start_date:
            query = query.where(AutoTrade.created_at >= start_date)
        
        if end_date:
            query = query.where(AutoTrade.created_at <= end_date)
        
        # Apply ordering and pagination
        query = query.order_by(desc(AutoTrade.created_at)).offset(offset).limit(limit)
        
        result = await db.execute(query)
        auto_trades = result.scalars().all()
        
        # Convert to response format
        response_trades = []
        for trade in auto_trades:
            response_trades.append(AutoTradeResponse(
                id=str(trade.id),
                symbol=trade.symbol,
                side=trade.side,
                quantity=trade.quantity,
                price=trade.price,
                executed_price=trade.executed_price,
                confidence=trade.confidence,
                expected_return=trade.expected_return,
                status=trade.status.value,
                reason=trade.reason.value,
                execution_time=trade.execution_time,
                realized_pnl=trade.realized_pnl,
                created_at=trade.created_at
            ))
        
        return response_trades
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting auto-trading history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get auto-trading history"
        )

@router.get("/analytics")
async def get_auto_trading_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get auto-trading analytics and performance metrics"""
    try:
        # Get trades from the last N days
        start_date = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            select(AutoTrade).where(
                and_(
                    AutoTrade.user_id == current_user.id,
                    AutoTrade.created_at >= start_date
                )
            )
        )
        trades = result.scalars().all()
        
        if not trades:
            return {
                "period_days": days,
                "total_trades": 0,
                "successful_trades": 0,
                "failed_trades": 0,
                "success_rate": 0.0,
                "total_pnl": 0.0,
                "average_return": 0.0,
                "average_confidence": 0.0,
                "most_traded_symbols": [],
                "daily_trade_count": []
            }
        
        # Calculate metrics
        total_trades = len(trades)
        successful_trades = len([t for t in trades if t.status == AutoTradeStatus.EXECUTED])
        failed_trades = len([t for t in trades if t.status == AutoTradeStatus.FAILED])
        success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Calculate P&L
        total_pnl = sum([t.realized_pnl or 0 for t in trades])
        average_return = sum([t.expected_return for t in trades]) / total_trades
        average_confidence = sum([t.confidence for t in trades]) / total_trades
        
        # Most traded symbols
        symbol_counts = {}
        for trade in trades:
            symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
        most_traded_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Daily trade counts
        daily_counts = {}
        for trade in trades:
            date_key = trade.created_at.strftime("%Y-%m-%d")
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        daily_trade_count = [{"date": k, "count": v} for k, v in sorted(daily_counts.items())]
        
        return {
            "period_days": days,
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "failed_trades": failed_trades,
            "success_rate": round(success_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "average_return": round(average_return * 100, 2),  # Convert to percentage
            "average_confidence": round(average_confidence * 100, 2),  # Convert to percentage
            "most_traded_symbols": [{"symbol": s, "count": c} for s, c in most_traded_symbols],
            "daily_trade_count": daily_trade_count
        }
        
    except Exception as e:
        logger.error(f"Error getting auto-trading analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get auto-trading analytics"
        )

@router.get("/market-status")
async def get_market_status():
    """Get current market status for auto-trading"""
    try:
        is_market_open = await auto_trading_service._is_market_open()
        
        return {
            "is_market_open": is_market_open,
            "market_hours": {
                "nse": {
                    "open": "09:15",
                    "close": "15:30",
                    "timezone": "Asia/Kolkata"
                },
                "bse": {
                    "open": "09:15", 
                    "close": "15:30",
                    "timezone": "Asia/Kolkata"
                }
            },
            "message": "Market is open" if is_market_open else "Market is closed"
        }
        
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get market status"
        )

# Manual intervention endpoints
class EmergencyStopRequest(BaseModel):
    reason: str = "Manual intervention"

class PauseRequest(BaseModel):
    duration_minutes: int = 30
    reason: str = "Manual pause"

@router.post("/emergency-stop")
async def emergency_stop_trading(
    request: EmergencyStopRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Emergency stop all auto-trading activity immediately"""
    try:
        success = await auto_trading_service.emergency_stop_all_trading(
            str(current_user.id), 
            request.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to execute emergency stop"
            )
        
        logger.warning(f"Emergency stop executed for user {current_user.email}: {request.reason}")
        
        return {
            "message": "Emergency stop executed successfully",
            "reason": request.reason,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "stopped"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing emergency stop: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute emergency stop"
        )

@router.post("/pause")
async def pause_auto_trading(
    request: PauseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Temporarily pause auto-trading for a specified duration"""
    try:
        if request.duration_minutes <= 0 or request.duration_minutes > 1440:  # Max 24 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duration must be between 1 and 1440 minutes (24 hours)"
            )
        
        success = await auto_trading_service.pause_auto_trading(
            str(current_user.id), 
            request.duration_minutes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to pause auto-trading"
            )
        
        logger.info(f"Auto-trading paused for user {current_user.email} for {request.duration_minutes} minutes")
        
        return {
            "message": f"Auto-trading paused for {request.duration_minutes} minutes",
            "duration_minutes": request.duration_minutes,
            "reason": request.reason,
            "paused_until": (datetime.utcnow() + timedelta(minutes=request.duration_minutes)).isoformat(),
            "status": "paused"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing auto-trading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause auto-trading"
        )

@router.post("/resume")
async def resume_auto_trading(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Resume auto-trading after manual pause"""
    try:
        success = await auto_trading_service.resume_auto_trading(str(current_user.id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to resume auto-trading or no active session found"
            )
        
        logger.info(f"Auto-trading resumed for user {current_user.email}")
        
        return {
            "message": "Auto-trading resumed successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming auto-trading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume auto-trading"
        )