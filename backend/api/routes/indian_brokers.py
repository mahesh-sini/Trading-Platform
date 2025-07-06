"""
Indian Broker API Routes
Specialized endpoints for Indian broker integrations with specific authentication flows
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any
from services.database import get_db
from models.broker import BrokerAccount, BrokerName, BrokerEnvironment, ConnectionStatus
from models.user import User
from app.services.brokers.broker_manager import broker_manager, BrokerType
from app.services.brokers.base_broker import BrokerCredentials
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models for Indian brokers
class ZerodhaKiteCredentials(BaseModel):
    api_key: str = Field(..., description="Zerodha API Key")
    api_secret: str = Field(..., description="Zerodha API Secret")
    request_token: Optional[str] = Field(None, description="Request token from Zerodha login")
    
class ICICIBreezeCredentials(BaseModel):
    api_key: str = Field(..., description="ICICI Breeze API Key")
    session_token: str = Field(..., description="ICICI Breeze Session Token")
    
class UpstoxCredentials(BaseModel):
    api_key: str = Field(..., description="Upstox API Key")
    api_secret: str = Field(..., description="Upstox API Secret")
    authorization_code: Optional[str] = Field(None, description="Authorization code from Upstox OAuth")
    redirect_uri: str = Field(..., description="Redirect URI for OAuth")
    
class AngelOneCredentials(BaseModel):
    api_key: str = Field(..., description="Angel One API Key")
    client_code: str = Field(..., description="Angel One Client Code")
    password: str = Field(..., description="Angel One Password")
    totp: str = Field(..., description="Angel One TOTP")

class IndianBrokerConnectionRequest(BaseModel):
    broker_name: str = Field(..., description="Indian broker name")
    credentials: Dict[str, Any] = Field(..., description="Broker-specific credentials")
    is_primary: bool = Field(False, description="Set as primary broker")
    
    @validator('broker_name')
    def validate_broker_name(cls, v):
        valid_indian_brokers = [
            BrokerName.ZERODHA_KITE.value,
            BrokerName.ICICI_BREEZE.value,
            BrokerName.UPSTOX.value,
            BrokerName.ANGEL_ONE.value
        ]
        if v not in valid_indian_brokers:
            raise ValueError(f'Broker must be one of: {valid_indian_brokers}')
        return v

class IndianBrokerConnectionResponse(BaseModel):
    account_id: str
    broker_name: str
    status: str
    balance: float
    buying_power: float
    currency: str
    is_primary: bool
    last_sync: Optional[str]
    created_at: str
    error_message: Optional[str] = None

class BrokerQuoteRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of Indian stock symbols")
    exchange: str = Field("NSE", description="Exchange (NSE/BSE)")

class BrokerQuoteResponse(BaseModel):
    symbol: str
    ltp: float
    change: float
    change_percent: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    high: float
    low: float
    open: float
    close: float
    timestamp: str

class OrderPlacementRequest(BaseModel):
    broker_id: str
    symbol: str
    quantity: int
    side: str  # BUY or SELL
    order_type: str  # MARKET, LIMIT, STOP_LIMIT
    price: Optional[float] = None
    stop_price: Optional[float] = None
    exchange: str = "NSE"

@router.get("/available-brokers")
async def get_available_indian_brokers():
    """Get list of available Indian brokers and their requirements"""
    return {
        "brokers": [
            {
                "name": "zerodha_kite",
                "display_name": "Zerodha Kite",
                "description": "India's largest retail broker",
                "website": "https://kite.trade",
                "credentials_required": [
                    {"field": "api_key", "type": "string", "description": "API Key from Kite Developer Console"},
                    {"field": "api_secret", "type": "string", "description": "API Secret from Kite Developer Console"},
                    {"field": "request_token", "type": "string", "description": "Request token from login flow", "optional": True}
                ],
                "features": ["stocks", "mutual_funds", "real_time_data"],
                "markets": ["NSE", "BSE"]
            },
            {
                "name": "icici_breeze",
                "display_name": "ICICI Breeze",
                "description": "ICICI Bank's trading platform",
                "website": "https://www.icicidirect.com",
                "credentials_required": [
                    {"field": "api_key", "type": "string", "description": "ICICI Breeze API Key"},
                    {"field": "session_token", "type": "string", "description": "Session token from ICICI Breeze"}
                ],
                "features": ["stocks", "options", "real_time_data"],
                "markets": ["NSE", "BSE"]
            },
            {
                "name": "upstox",
                "display_name": "Upstox",
                "description": "Technology-first brokerage platform",
                "website": "https://upstox.com",
                "credentials_required": [
                    {"field": "api_key", "type": "string", "description": "Upstox API Key"},
                    {"field": "api_secret", "type": "string", "description": "Upstox API Secret"},
                    {"field": "redirect_uri", "type": "string", "description": "OAuth redirect URI"},
                    {"field": "authorization_code", "type": "string", "description": "OAuth authorization code", "optional": True}
                ],
                "features": ["stocks", "options", "real_time_data"],
                "markets": ["NSE", "BSE"]
            },
            {
                "name": "angel_one",
                "display_name": "Angel One",
                "description": "Full-service stockbroker",
                "website": "https://www.angelone.in",
                "credentials_required": [
                    {"field": "api_key", "type": "string", "description": "Angel One API Key"},
                    {"field": "client_code", "type": "string", "description": "Angel One Client Code"},
                    {"field": "password", "type": "password", "description": "Angel One Password"},
                    {"field": "totp", "type": "string", "description": "TOTP from authenticator app"}
                ],
                "features": ["stocks", "options", "mutual_funds", "real_time_data"],
                "markets": ["NSE", "BSE"]
            }
        ]
    }

@router.post("/test-connection")
async def test_indian_broker_connection(connection_request: IndianBrokerConnectionRequest):
    """Test connection to Indian broker without saving credentials"""
    try:
        broker_type_map = {
            BrokerName.ZERODHA_KITE.value: BrokerType.ZERODHA_KITE,
            BrokerName.ICICI_BREEZE.value: BrokerType.ICICI_BREEZE,
            BrokerName.UPSTOX.value: BrokerType.UPSTOX,
            BrokerName.ANGEL_ONE.value: BrokerType.ANGEL_ONE
        }
        
        broker_type = broker_type_map.get(connection_request.broker_name)
        if not broker_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported broker: {connection_request.broker_name}"
            )
        
        # Create broker credentials
        credentials = BrokerCredentials(
            api_key=connection_request.credentials.get('api_key', ''),
            secret_key=connection_request.credentials.get('api_secret', '') or 
                      connection_request.credentials.get('password', ''),
            sandbox=True,  # Test in sandbox mode
            additional_params=connection_request.credentials
        )
        
        # Test connection
        test_broker_id = f"test_{broker_type.value}_{datetime.now().timestamp()}"
        success = await broker_manager.add_broker(test_broker_id, broker_type, credentials)
        
        if success:
            # Get account info to verify connection
            account_info = await broker_manager.get_account_info(test_broker_id)
            
            # Clean up test connection
            await broker_manager.remove_broker(test_broker_id)
            
            return {
                "status": "connected",
                "message": "Connection successful",
                "account_info": {
                    "account_id": account_info.account_id,
                    "currency": account_info.currency,
                    "buying_power": float(account_info.buying_power)
                }
            }
        else:
            return {
                "status": "failed",
                "message": "Connection failed - invalid credentials"
            }
        
    except Exception as e:
        logger.error(f"Indian broker connection test failed: {str(e)}")
        return {
            "status": "failed", 
            "message": f"Connection test failed: {str(e)}"
        }

@router.post("/connect", response_model=IndianBrokerConnectionResponse)
async def connect_indian_broker(
    connection_request: IndianBrokerConnectionRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Connect to an Indian broker and save credentials"""
    try:
        user_id = current_user.get("sub")
        
        # Check if user already has an account with this broker
        result = await db.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.user_id == user_id,
                    BrokerAccount.broker_name == BrokerName(connection_request.broker_name),
                    BrokerAccount.environment == BrokerEnvironment.LIVE
                )
            )
        )
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account already exists for {connection_request.broker_name}"
            )
        
        # Map broker names to types
        broker_type_map = {
            BrokerName.ZERODHA_KITE.value: BrokerType.ZERODHA_KITE,
            BrokerName.ICICI_BREEZE.value: BrokerType.ICICI_BREEZE,
            BrokerName.UPSTOX.value: BrokerType.UPSTOX,
            BrokerName.ANGEL_ONE.value: BrokerType.ANGEL_ONE
        }
        
        broker_type = broker_type_map.get(connection_request.broker_name)
        if not broker_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported broker: {connection_request.broker_name}"
            )
        
        # Create broker credentials
        credentials = BrokerCredentials(
            api_key=connection_request.credentials.get('api_key', ''),
            secret_key=connection_request.credentials.get('api_secret', '') or 
                      connection_request.credentials.get('password', ''),
            sandbox=False,  # Live connection
            additional_params=connection_request.credentials
        )
        
        # Create database record first
        broker_account = BrokerAccount(
            user_id=user_id,
            broker_name=BrokerName(connection_request.broker_name),
            api_key=connection_request.credentials.get('api_key', ''),  # TODO: Encrypt in production
            api_secret=connection_request.credentials.get('api_secret', '') or 
                      connection_request.credentials.get('password', ''),  # TODO: Encrypt in production
            environment=BrokerEnvironment.LIVE,
            is_primary=connection_request.is_primary,
            status=ConnectionStatus.PENDING,
            settings=str(connection_request.credentials)  # Store additional params
        )
        
        db.add(broker_account)
        await db.commit()
        await db.refresh(broker_account)
        
        broker_id = str(broker_account.id)
        
        try:
            # Test connection and add to broker manager
            await broker_manager.add_broker(broker_id, broker_type, credentials, make_default=connection_request.is_primary)
            
            # Get account info
            account_info = await broker_manager.get_account_info(broker_id)
            
            # Update database with account info
            broker_account.status = ConnectionStatus.CONNECTED
            broker_account.balance = float(account_info.cash)
            broker_account.buying_power = float(account_info.buying_power)
            broker_account.day_trading_buying_power = float(account_info.day_trading_buying_power or 0)
            broker_account.last_sync = datetime.utcnow()
            broker_account.account_number = account_info.account_id
            
            await db.commit()
            
            logger.info(f"Indian broker connected successfully: {broker_id}")
            
            return IndianBrokerConnectionResponse(
                account_id=broker_id,
                broker_name=connection_request.broker_name,
                status=ConnectionStatus.CONNECTED.value,
                balance=float(account_info.cash),
                buying_power=float(account_info.buying_power),
                currency=account_info.currency,
                is_primary=connection_request.is_primary,
                last_sync=broker_account.last_sync.isoformat(),
                created_at=broker_account.created_at.isoformat()
            )
            
        except Exception as e:
            # Update status to error
            broker_account.status = ConnectionStatus.ERROR
            broker_account.error_message = str(e)
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to {connection_request.broker_name}: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect Indian broker: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect broker"
        )

@router.get("/connections", response_model=List[IndianBrokerConnectionResponse])
async def get_indian_broker_connections(
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Get user's Indian broker connections"""
    try:
        user_id = current_user.get("sub")
        
        # Get Indian broker accounts only
        indian_brokers = [
            BrokerName.ZERODHA_KITE,
            BrokerName.ICICI_BREEZE,
            BrokerName.UPSTOX,
            BrokerName.ANGEL_ONE
        ]
        
        result = await db.execute(
            select(BrokerAccount)
            .where(
                and_(
                    BrokerAccount.user_id == user_id,
                    BrokerAccount.broker_name.in_(indian_brokers),
                    BrokerAccount.is_active == True
                )
            )
            .order_by(BrokerAccount.is_primary.desc(), BrokerAccount.created_at.desc())
        )
        accounts = result.scalars().all()
        
        connections = []
        for account in accounts:
            connections.append(IndianBrokerConnectionResponse(
                account_id=str(account.id),
                broker_name=account.broker_name.value,
                status=account.status.value,
                balance=account.balance,
                buying_power=account.buying_power,
                currency="INR",
                is_primary=account.is_primary,
                last_sync=account.last_sync.isoformat() if account.last_sync else None,
                created_at=account.created_at.isoformat(),
                error_message=account.error_message
            ))
        
        return connections
        
    except Exception as e:
        logger.error(f"Failed to get Indian broker connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve broker connections"
        )

@router.post("/quotes", response_model=List[BrokerQuoteResponse])
async def get_indian_market_quotes(
    quote_request: BrokerQuoteRequest,
    broker_id: Optional[str] = None,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"})  # TODO: Replace with actual auth
):
    """Get real-time quotes for Indian stocks"""
    try:
        # Use default broker if none specified
        if not broker_id:
            broker_connections = broker_manager.list_brokers()
            if not broker_connections:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No broker connections available"
                )
            broker_id = broker_manager.default_broker
        
        # Get quotes from broker
        quotes_data = await broker_manager.get_quotes(quote_request.symbols, broker_id)
        
        quotes = []
        for symbol, quote in quotes_data.items():
            quotes.append(BrokerQuoteResponse(
                symbol=symbol,
                ltp=float(quote.last),
                change=float(quote.last - quote.close) if quote.close else 0.0,
                change_percent=float((quote.last - quote.close) / quote.close * 100) if quote.close else 0.0,
                volume=quote.volume or 0,
                bid=float(quote.bid) if quote.bid else None,
                ask=float(quote.ask) if quote.ask else None,
                high=float(quote.high) if quote.high else float(quote.last),
                low=float(quote.low) if quote.low else float(quote.last),
                open=float(quote.open) if quote.open else float(quote.last),
                close=float(quote.close) if quote.close else float(quote.last),
                timestamp=quote.timestamp.isoformat()
            ))
        
        return quotes
        
    except Exception as e:
        logger.error(f"Failed to get market quotes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market quotes"
        )

@router.post("/place-order")
async def place_order_with_indian_broker(
    order_request: OrderPlacementRequest,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"})  # TODO: Replace with actual auth
):
    """Place order through Indian broker"""
    try:
        from app.services.brokers.base_broker import OrderRequest, OrderType, OrderSide, AssetType
        
        # Map order types and sides
        order_type_map = {
            "MARKET": OrderType.MARKET,
            "LIMIT": OrderType.LIMIT,
            "STOP_LIMIT": OrderType.STOP_LIMIT
        }
        
        order_side_map = {
            "BUY": OrderSide.BUY,
            "SELL": OrderSide.SELL
        }
        
        # Create order request
        broker_order = OrderRequest(
            symbol=order_request.symbol,
            quantity=order_request.quantity,
            side=order_side_map[order_request.side],
            order_type=order_type_map[order_request.order_type],
            price=order_request.price,
            stop_price=order_request.stop_price,
            asset_type=AssetType.STOCK
        )
        
        # Place order
        order_response = await broker_manager.place_order(broker_order, order_request.broker_id)
        
        return {
            "order_id": order_response.order_id,
            "status": order_response.status.value,
            "symbol": order_response.symbol,
            "quantity": order_response.quantity,
            "message": "Order placed successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to place order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place order: {str(e)}"
        )

@router.get("/market-status")
async def get_indian_market_status():
    """Get Indian market status"""
    try:
        # Check if any broker is connected
        broker_connections = broker_manager.list_brokers()
        if broker_connections:
            # Use first available broker to check market status
            broker_id = next(iter(broker_connections.keys()))
            is_open = await broker_manager.is_market_open(broker_id)
        else:
            # Fallback to time-based check
            import pytz
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            # Check if weekday and trading hours
            is_open = (
                now.weekday() < 5 and  # Monday to Friday
                now.replace(hour=9, minute=15, second=0, microsecond=0) <= now <= 
                now.replace(hour=15, minute=30, second=0, microsecond=0)
            )
        
        return {
            "market_open": is_open,
            "exchange": "NSE/BSE",
            "timezone": "Asia/Kolkata",
            "trading_hours": "09:15 - 15:30 IST",
            "currency": "INR"
        }
        
    except Exception as e:
        logger.error(f"Failed to get market status: {str(e)}")
        return {
            "market_open": False,
            "error": "Unable to determine market status"
        }