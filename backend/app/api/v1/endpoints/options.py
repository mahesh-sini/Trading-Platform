"""
Options Trading API endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.options import OptionsContract, OptionsPosition, OptionsOrder, OptionsStrategy
from app.services.options_trading import (
    OptionsContractService, OptionsPositionService, 
    OptionsOrderService, OptionsStrategyService
)
from app.services.rbac import RBACService
from app.schemas.options import (
    OptionsChainResponse, OptionsPositionResponse, OptionsOrderCreate,
    OptionsOrderResponse, OptionsStrategyCreate, OptionsStrategyResponse,
    OptionsContractResponse, GreeksResponse
)

router = APIRouter()


# Options Chain and Contracts
@router.get("/chain/{underlying_symbol}", response_model=List[OptionsContractResponse])
async def get_options_chain(
    underlying_symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    expiration_date: Optional[datetime] = Query(None)
):
    """Get options chain for a symbol"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.view_orders", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view options data"
        )
    
    contract_service = OptionsContractService(db)
    contracts = await contract_service.get_options_chain(
        underlying_symbol.upper(), expiration_date
    )
    
    return [OptionsContractResponse.from_orm(contract) for contract in contracts]


@router.get("/expirations/{underlying_symbol}")
async def get_expiration_dates(
    underlying_symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all available expiration dates for a symbol"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.view_orders", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    contract_service = OptionsContractService(db)
    expiration_dates = await contract_service.get_expiration_dates(underlying_symbol.upper())
    
    return {
        "underlying_symbol": underlying_symbol.upper(),
        "expiration_dates": [date.isoformat() for date in expiration_dates]
    }


@router.get("/contract/{symbol}", response_model=OptionsContractResponse)
async def get_options_contract(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific options contract by symbol"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.view_orders", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    contract_service = OptionsContractService(db)
    contract = await contract_service.get_contract_by_symbol(symbol.upper())
    
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Options contract not found"
        )
    
    return OptionsContractResponse.from_orm(contract)


# Options Positions
@router.get("/positions", response_model=List[OptionsPositionResponse])
async def get_options_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    portfolio_id: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """Get user's options positions"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "portfolio.read", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view positions"
        )
    
    position_service = OptionsPositionService(db)
    positions = await position_service.get_user_positions(
        str(current_user.id), str(current_user.organization_id),
        portfolio_id, active_only
    )
    
    return [OptionsPositionResponse.from_orm(position) for position in positions]


@router.get("/positions/{position_id}", response_model=OptionsPositionResponse)
async def get_options_position(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific options position"""
    position = await db.get(OptionsPosition, position_id)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    # Check if user owns the position
    if (str(position.user_id) != str(current_user.id) or 
        str(position.organization_id) != str(current_user.organization_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return OptionsPositionResponse.from_orm(position)


@router.post("/positions/{position_id}/close")
async def close_options_position(
    position_id: str,
    close_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Close an options position"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.place_order", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to close positions"
        )
    
    position_service = OptionsPositionService(db)
    position = await position_service.close_position(
        position_id, str(current_user.id), close_data.get("closing_price", 0)
    )
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    return {"message": "Position closed successfully"}


# Options Orders
@router.post("/orders", response_model=OptionsOrderResponse)
async def place_options_order(
    order_data: OptionsOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Place an options order"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.place_order", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to place orders"
        )
    
    # Validate contract exists
    contract_service = OptionsContractService(db)
    contract = await contract_service.get_contract_by_symbol(order_data.contract_symbol)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Options contract not found"
        )
    
    # Create order
    order_service = OptionsOrderService(db)
    order_dict = order_data.dict()
    order_dict.update({
        'organization_id': str(current_user.organization_id),
        'user_id': str(current_user.id),
        'contract_id': str(contract.id)
    })
    
    order = await order_service.place_order(order_dict)
    
    return OptionsOrderResponse.from_orm(order)


@router.get("/orders", response_model=List[OptionsOrderResponse])
async def get_options_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, le=1000)
):
    """Get user's options orders"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.view_orders", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view orders"
        )
    
    order_service = OptionsOrderService(db)
    orders = await order_service.get_user_orders(
        str(current_user.id), str(current_user.organization_id),
        status_filter, limit
    )
    
    return [OptionsOrderResponse.from_orm(order) for order in orders]


@router.post("/orders/{order_id}/cancel")
async def cancel_options_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an options order"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.cancel_order", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to cancel orders"
        )
    
    order_service = OptionsOrderService(db)
    order = await order_service.cancel_order(order_id, str(current_user.id))
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or cannot be cancelled"
        )
    
    return {"message": "Order cancelled successfully"}


# Options Strategies
@router.post("/strategies", response_model=OptionsStrategyResponse)
async def create_options_strategy(
    strategy_data: OptionsStrategyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create an options strategy"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.place_order", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create strategies"
        )
    
    strategy_service = OptionsStrategyService(db)
    strategy_dict = strategy_data.dict()
    strategy_dict.update({
        'organization_id': str(current_user.organization_id),
        'user_id': str(current_user.id)
    })
    
    strategy = await strategy_service.create_strategy(strategy_dict)
    
    return OptionsStrategyResponse.from_orm(strategy)


@router.get("/strategies", response_model=List[OptionsStrategyResponse])
async def get_options_strategies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's options strategies"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "portfolio.read", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view strategies"
        )
    
    strategy_service = OptionsStrategyService(db)
    strategies = await strategy_service.get_user_strategies(
        str(current_user.id), str(current_user.organization_id)
    )
    
    return [OptionsStrategyResponse.from_orm(strategy) for strategy in strategies]


@router.get("/strategies/{strategy_id}/analysis")
async def analyze_options_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    underlying_price: float = Query(..., description="Current underlying price")
):
    """Get strategy analysis including payoff diagram and Greeks"""
    strategy = await db.get(OptionsStrategy, strategy_id)
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Check ownership
    if (str(strategy.user_id) != str(current_user.id) or 
        str(strategy.organization_id) != str(current_user.organization_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    strategy_service = OptionsStrategyService(db)
    analysis = await strategy_service.calculate_strategy_metrics(
        strategy, underlying_price
    )
    
    return {
        "strategy_id": strategy_id,
        "underlying_price": underlying_price,
        "analysis": analysis
    }


# Strategy Templates
@router.get("/strategies/templates")
async def get_strategy_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get predefined options strategy templates"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.view_orders", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    templates = [
        {
            "name": "Covered Call",
            "type": "covered_call",
            "description": "Own stock and sell call options for income",
            "market_outlook": "Neutral to slightly bullish",
            "max_profit": "Limited to call premium + (strike - stock price)",
            "max_loss": "Stock price decline to zero (minus call premium)",
            "complexity": "Beginner"
        },
        {
            "name": "Protective Put",
            "type": "protective_put",
            "description": "Own stock and buy put options for protection",
            "market_outlook": "Bullish with downside protection",
            "max_profit": "Unlimited (stock appreciation minus put premium)",
            "max_loss": "Limited to (stock price - strike + put premium)",
            "complexity": "Beginner"
        },
        {
            "name": "Long Straddle",
            "type": "long_straddle",
            "description": "Buy call and put with same strike and expiration",
            "market_outlook": "High volatility expected",
            "max_profit": "Unlimited",
            "max_loss": "Total premium paid",
            "complexity": "Intermediate"
        },
        {
            "name": "Iron Condor",
            "type": "iron_condor",
            "description": "Sell put spread and call spread",
            "market_outlook": "Low volatility (range-bound)",
            "max_profit": "Net premium received",
            "max_loss": "Strike width minus net premium",
            "complexity": "Advanced"
        },
        {
            "name": "Bull Call Spread",
            "type": "bull_call_spread",
            "description": "Buy lower strike call, sell higher strike call",
            "market_outlook": "Moderately bullish",
            "max_profit": "Strike difference minus net premium",
            "max_loss": "Net premium paid",
            "complexity": "Intermediate"
        }
    ]
    
    return {"templates": templates}


@router.post("/strategies/templates/{template_type}")
async def create_strategy_from_template(
    template_type: str,
    template_params: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a strategy from a predefined template"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "trading.place_order", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create strategies"
        )
    
    strategy_service = OptionsStrategyService(db)
    
    # Create strategy based on template
    if template_type == "covered_call":
        strategy_def = strategy_service.create_covered_call_strategy(
            template_params["underlying_symbol"],
            template_params["stock_quantity"],
            template_params["call_strike"],
            datetime.fromisoformat(template_params["call_expiration"])
        )
    elif template_type == "protective_put":
        strategy_def = strategy_service.create_protective_put_strategy(
            template_params["underlying_symbol"],
            template_params["stock_quantity"],
            template_params["put_strike"],
            datetime.fromisoformat(template_params["put_expiration"])
        )
    elif template_type == "iron_condor":
        strategy_def = strategy_service.create_iron_condor_strategy(
            template_params["underlying_symbol"],
            template_params["put_strike_short"],
            template_params["put_strike_long"],
            template_params["call_strike_short"],
            template_params["call_strike_long"],
            datetime.fromisoformat(template_params["expiration"])
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown strategy template: {template_type}"
        )
    
    # Add required fields
    strategy_def.update({
        'organization_id': str(current_user.organization_id),
        'user_id': str(current_user.id),
        'portfolio_id': template_params["portfolio_id"],
        'name': template_params.get("name", f"{template_type.replace('_', ' ').title()} Strategy")
    })
    
    strategy = await strategy_service.create_strategy(strategy_def)
    
    return OptionsStrategyResponse.from_orm(strategy)


# Greeks and Risk Analysis
@router.get("/positions/{position_id}/greeks", response_model=GreeksResponse)
async def get_position_greeks(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    underlying_price: float = Query(..., description="Current underlying price")
):
    """Get Greeks for an options position"""
    position = await db.get(OptionsPosition, position_id)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    # Check ownership
    if (str(position.user_id) != str(current_user.id) or 
        str(position.organization_id) != str(current_user.organization_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    position_service = OptionsPositionService(db)
    greeks = await position_service.calculate_position_greeks(position, underlying_price)
    
    return GreeksResponse(**greeks)