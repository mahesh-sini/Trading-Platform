"""
Broker Management API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.services.brokers.broker_manager import broker_manager, BrokerType
from app.services.brokers.base_broker import (
    BrokerCredentials, OrderRequest, OrderResponse, Quote, Position, 
    AccountInfo, HistoricalBar, OrderStatus
)

router = APIRouter()


class BrokerCredentialsRequest(BaseModel):
    """Request model for broker credentials"""
    api_key: str
    secret_key: str
    account_id: Optional[str] = None
    sandbox: bool = True
    additional_params: Optional[Dict[str, Any]] = None


class AddBrokerRequest(BaseModel):
    """Request model for adding a broker"""
    broker_id: str = Field(..., min_length=1, max_length=50)
    broker_type: str = Field(..., description="Broker type (interactive_brokers, td_ameritrade, etrade)")
    credentials: BrokerCredentialsRequest
    make_default: bool = False


class OrderRequestModel(BaseModel):
    """Request model for placing orders"""
    symbol: str
    quantity: int = Field(..., gt=0)
    side: str = Field(..., regex=r"^(buy|sell|buy_to_cover|sell_short)$")
    order_type: str = Field(..., regex=r"^(market|limit|stop|stop_limit|trailing_stop)$")
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = Field("DAY", regex=r"^(DAY|GTC|IOC|FOK)$")
    asset_type: str = Field("stock", regex=r"^(stock|option|etf|mutual_fund|bond|crypto|forex)$")
    broker_id: Optional[str] = None


class QuoteRequest(BaseModel):
    """Request model for getting quotes"""
    symbols: List[str] = Field(..., min_items=1, max_items=50)
    broker_id: Optional[str] = None


class HistoricalDataRequest(BaseModel):
    """Request model for historical data"""
    symbol: str
    period: str = Field("1d", regex=r"^(1m|5m|15m|30m|1h|1d|1w|1mo)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: Optional[int] = Field(None, ge=1, le=1000)
    broker_id: Optional[str] = None


@router.post("/brokers", status_code=status.HTTP_201_CREATED)
async def add_broker(
    request: AddBrokerRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("broker:manage"))
):
    """Add a new broker connection"""
    try:
        # Validate broker type
        try:
            broker_type = BrokerType(request.broker_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid broker type: {request.broker_type}"
            )
        
        # Convert credentials
        credentials = BrokerCredentials(
            api_key=request.credentials.api_key,
            secret_key=request.credentials.secret_key,
            account_id=request.credentials.account_id,
            sandbox=request.credentials.sandbox,
            additional_params=request.credentials.additional_params
        )
        
        # Add broker
        success = await broker_manager.add_broker(
            broker_id=request.broker_id,
            broker_type=broker_type,
            credentials=credentials,
            make_default=request.make_default
        )
        
        if success:
            return {
                "message": f"Broker {request.broker_id} added successfully",
                "broker_id": request.broker_id,
                "broker_type": request.broker_type,
                "is_default": request.make_default
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add broker"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/brokers")
async def list_brokers(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("broker:read"))
):
    """List all configured brokers"""
    try:
        brokers = broker_manager.list_brokers()
        return {
            "brokers": brokers,
            "total_count": len(brokers),
            "default_broker": broker_manager.default_broker
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/brokers/{broker_id}")
async def remove_broker(
    broker_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("broker:manage"))
):
    """Remove a broker connection"""
    try:
        success = await broker_manager.remove_broker(broker_id)
        
        if success:
            return {"message": f"Broker {broker_id} removed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Broker {broker_id} not found"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/brokers/{broker_id}/default")
async def set_default_broker(
    broker_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("broker:manage"))
):
    """Set default broker"""
    try:
        success = await broker_manager.set_default_broker(broker_id)
        
        if success:
            return {"message": f"Broker {broker_id} set as default"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Broker {broker_id} not found"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/brokers/health")
async def broker_health_check(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("broker:read"))
):
    """Check health of all broker connections"""
    try:
        health_status = await broker_manager.health_check()
        return {"health_status": health_status}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/brokers/{broker_id}/capabilities")
async def get_broker_capabilities(
    broker_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("broker:read"))
):
    """Get broker capabilities"""
    try:
        capabilities = broker_manager.get_broker_capabilities(broker_id)
        return capabilities
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/accounts")
async def get_accounts(
    broker_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("trading:read"))
):
    """Get account information"""
    try:
        if broker_id:
            account_info = await broker_manager.get_account_info(broker_id)
            return {"account": account_info.__dict__}
        else:
            accounts = await broker_manager.get_all_accounts_info()
            return {
                "accounts": {
                    broker_id: account.__dict__ 
                    for broker_id, account in accounts.items()
                }
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/positions")
async def get_positions(
    broker_id: Optional[str] = None,
    consolidated: bool = False,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("trading:read"))
):
    """Get positions"""
    try:
        if consolidated:
            positions = await broker_manager.get_consolidated_positions()
            return {"positions": [pos.__dict__ for pos in positions]}
        elif broker_id:
            positions = await broker_manager.get_positions(broker_id)
            return {"positions": [pos.__dict__ for pos in positions]}
        else:
            all_positions = await broker_manager.get_all_positions()
            return {
                "positions": {
                    broker_id: [pos.__dict__ for pos in positions]
                    for broker_id, positions in all_positions.items()
                }
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/quotes")
async def get_quotes(
    request: QuoteRequest,
    best_execution: bool = False,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("market_data:read"))
):
    """Get quotes for symbols"""
    try:
        quotes = {}
        
        for symbol in request.symbols:
            if best_execution:
                quote = await broker_manager.get_best_quote(symbol)
            else:
                quote = await broker_manager.get_quote(symbol, request.broker_id)
            quotes[symbol] = quote.__dict__
        
        return {"quotes": quotes}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/orders")
async def place_order(
    request: OrderRequestModel,
    smart_routing: bool = False,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("trading:execute"))
):
    """Place a trading order"""
    try:
        # Convert request to OrderRequest
        from app.services.brokers.base_broker import OrderRequest, OrderSide, OrderType, AssetType
        from decimal import Decimal
        
        order = OrderRequest(
            symbol=request.symbol,
            quantity=request.quantity,
            side=OrderSide(request.side),
            order_type=OrderType(request.order_type),
            price=Decimal(str(request.price)) if request.price else None,
            stop_price=Decimal(str(request.stop_price)) if request.stop_price else None,
            time_in_force=request.time_in_force,
            asset_type=AssetType(request.asset_type)
        )
        
        # Place order
        if smart_routing:
            order_response = await broker_manager.smart_order_routing(order)
        else:
            order_response = await broker_manager.place_order(order, request.broker_id)
        
        return {"order": order_response.__dict__}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    broker_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("trading:execute"))
):
    """Cancel an order"""
    try:
        success = await broker_manager.cancel_order(order_id, broker_id)
        
        if success:
            return {"message": f"Order {order_id} cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to cancel order {order_id}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/orders/{order_id}")
async def get_order_status(
    order_id: str,
    broker_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("trading:read"))
):
    """Get order status"""
    try:
        order = await broker_manager.get_order_status(order_id, broker_id)
        return {"order": order.__dict__}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/orders")
async def get_orders(
    broker_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    all_brokers: bool = False,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("trading:read"))
):
    """Get order history"""
    try:
        order_status = OrderStatus(status) if status else None
        
        if all_brokers:
            orders = await broker_manager.get_all_orders(order_status, start_date, end_date)
            return {
                "orders": {
                    broker_id: [order.__dict__ for order in order_list]
                    for broker_id, order_list in orders.items()
                }
            }
        else:
            orders = await broker_manager.get_orders(broker_id, order_status, start_date, end_date)
            return {"orders": [order.__dict__ for order in orders]}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/historical-data")
async def get_historical_data(
    request: HistoricalDataRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("market_data:read"))
):
    """Get historical price data"""
    try:
        bars = await broker_manager.get_historical_data(
            symbol=request.symbol,
            period=request.period,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            broker_id=request.broker_id
        )
        
        return {
            "symbol": request.symbol,
            "period": request.period,
            "bars": [bar.__dict__ for bar in bars],
            "count": len(bars)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/options-chain/{underlying_symbol}")
async def get_options_chain(
    underlying_symbol: str,
    expiration_date: Optional[datetime] = None,
    broker_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("market_data:read"))
):
    """Get options chain"""
    try:
        chain = await broker_manager.get_options_chain(
            underlying_symbol=underlying_symbol,
            expiration_date=expiration_date,
            broker_id=broker_id
        )
        
        return {
            "underlying_symbol": underlying_symbol,
            "chain": chain
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )