from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from services.database import get_db
from services.broker_service import trading_service, BrokerType
from models.broker import BrokerAccount, BrokerName, BrokerEnvironment, ConnectionStatus
from models.user import User
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class BrokerAccountRequest(BaseModel):
    broker_name: str
    api_key: str
    api_secret: str
    environment: str = "paper"  # paper or live
    is_primary: bool = False
    
    @validator('broker_name')
    def validate_broker_name(cls, v):
        valid_brokers = [broker.value for broker in BrokerName]
        if v not in valid_brokers:
            raise ValueError(f'Broker must be one of: {valid_brokers}')
        return v
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in ['paper', 'live']:
            raise ValueError('Environment must be paper or live')
        return v

class BrokerAccountResponse(BaseModel):
    account_id: str
    broker_name: str
    environment: str
    status: str
    balance: float
    buying_power: float
    day_trading_buying_power: float
    portfolio_value: float
    is_primary: bool
    last_sync: Optional[str]
    created_at: str

class ConnectionTestRequest(BaseModel):
    broker_name: str
    api_key: str
    api_secret: str
    environment: str = "paper"

@router.post("/accounts", response_model=BrokerAccountResponse)
async def add_broker_account(
    account_request: BrokerAccountRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Add a new broker account"""
    try:
        user_id = current_user.get("sub")
        
        # Check if user already has an account with this broker
        result = await db.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.user_id == user_id,
                    BrokerAccount.broker_name == BrokerName(account_request.broker_name),
                    BrokerAccount.environment == BrokerEnvironment(account_request.environment)
                )
            )
        )
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account already exists for {account_request.broker_name} in {account_request.environment} environment"
            )
        
        # Test connection first
        broker_type = BrokerType(account_request.broker_name)
        credentials = {
            "api_key": account_request.api_key,
            "api_secret": account_request.api_secret,
            "base_url": "https://paper-api.alpaca.markets" if account_request.environment == "paper" else "https://api.alpaca.markets"
        }
        
        connection_success = await trading_service.test_broker_connection(broker_type, credentials)
        
        if not connection_success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to connect to broker with provided credentials"
            )
        
        # Create broker account
        broker_account = BrokerAccount(
            user_id=user_id,
            broker_name=BrokerName(account_request.broker_name),
            api_key=account_request.api_key,  # TODO: Encrypt in production
            api_secret=account_request.api_secret,  # TODO: Encrypt in production
            environment=BrokerEnvironment(account_request.environment),
            is_primary=account_request.is_primary,
            status=ConnectionStatus.CONNECTED
        )
        
        db.add(broker_account)
        await db.commit()
        await db.refresh(broker_account)
        
        # Add broker connection to trading service
        broker_id = str(broker_account.id)
        await trading_service.add_broker_connection(broker_id, broker_type, credentials)
        
        # Sync account data in background
        background_tasks.add_task(sync_broker_account_data, broker_id, db)
        
        logger.info(f"Broker account added successfully: {broker_id}")
        
        return BrokerAccountResponse(
            account_id=str(broker_account.id),
            broker_name=broker_account.broker_name.value,
            environment=broker_account.environment.value,
            status=broker_account.status.value,
            balance=broker_account.balance,
            buying_power=broker_account.buying_power,
            day_trading_buying_power=broker_account.day_trading_buying_power,
            portfolio_value=broker_account.portfolio_value,
            is_primary=broker_account.is_primary,
            last_sync=broker_account.last_sync.isoformat() if broker_account.last_sync else None,
            created_at=broker_account.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add broker account: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add broker account"
        )

@router.get("/accounts", response_model=List[BrokerAccountResponse])
async def get_broker_accounts(
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Get user's broker accounts"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(
            select(BrokerAccount)
            .where(BrokerAccount.user_id == user_id)
            .order_by(BrokerAccount.is_primary.desc(), BrokerAccount.created_at.desc())
        )
        accounts = result.scalars().all()
        
        return [
            BrokerAccountResponse(
                account_id=str(account.id),
                broker_name=account.broker_name.value,
                environment=account.environment.value,
                status=account.status.value,
                balance=account.balance,
                buying_power=account.buying_power,
                day_trading_buying_power=account.day_trading_buying_power,
                portfolio_value=account.portfolio_value,
                is_primary=account.is_primary,
                last_sync=account.last_sync.isoformat() if account.last_sync else None,
                created_at=account.created_at.isoformat()
            )
            for account in accounts
        ]
        
    except Exception as e:
        logger.error(f"Failed to get broker accounts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve broker accounts"
        )

@router.get("/accounts/{account_id}", response_model=BrokerAccountResponse)
async def get_broker_account(
    account_id: str,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Get specific broker account details"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.id == account_id,
                    BrokerAccount.user_id == user_id
                )
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker account not found"
            )
        
        return BrokerAccountResponse(
            account_id=str(account.id),
            broker_name=account.broker_name.value,
            environment=account.environment.value,
            status=account.status.value,
            balance=account.balance,
            buying_power=account.buying_power,
            day_trading_buying_power=account.day_trading_buying_power,
            portfolio_value=account.portfolio_value,
            is_primary=account.is_primary,
            last_sync=account.last_sync.isoformat() if account.last_sync else None,
            created_at=account.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get broker account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve broker account"
        )

@router.post("/test-connection")
async def test_broker_connection(
    connection_test: ConnectionTestRequest
):
    """Test broker connection without saving credentials"""
    try:
        broker_type = BrokerType(connection_test.broker_name)
        credentials = {
            "api_key": connection_test.api_key,
            "api_secret": connection_test.api_secret,
            "base_url": "https://paper-api.alpaca.markets" if connection_test.environment == "paper" else "https://api.alpaca.markets"
        }
        
        success = await trading_service.test_broker_connection(broker_type, credentials)
        
        return {
            "status": "connected" if success else "failed",
            "message": "Connection successful" if success else "Connection failed"
        }
        
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return {
            "status": "failed",
            "message": f"Connection test failed: {str(e)}"
        }

@router.post("/accounts/{account_id}/sync")
async def sync_broker_account(
    account_id: str,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Sync broker account data"""
    try:
        user_id = current_user.get("sub")
        
        # Verify account belongs to user
        result = await db.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.id == account_id,
                    BrokerAccount.user_id == user_id
                )
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker account not found"
            )
        
        # Sync account data
        success = await sync_broker_account_data(account_id, db)
        
        if success:
            return {"message": "Account data synced successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync account data"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync broker account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync account data"
        )

@router.delete("/accounts/{account_id}")
async def remove_broker_account(
    account_id: str,
    current_user: dict = Depends(lambda: {"sub": "test-user-id"}),  # TODO: Replace with actual auth
    db: AsyncSession = Depends(get_db)
):
    """Remove broker account"""
    try:
        user_id = current_user.get("sub")
        
        # Verify account belongs to user
        result = await db.execute(
            select(BrokerAccount).where(
                and_(
                    BrokerAccount.id == account_id,
                    BrokerAccount.user_id == user_id
                )
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Broker account not found"
            )
        
        # Remove from trading service
        await trading_service.remove_broker_connection(account_id)
        
        # Soft delete from database
        account.is_active = False
        account.status = ConnectionStatus.DISCONNECTED
        await db.commit()
        
        logger.info(f"Broker account removed: {account_id}")
        
        return {"message": "Broker account removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove broker account: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove broker account"
        )

# Background task functions
async def sync_broker_account_data(broker_id: str, db: AsyncSession) -> bool:
    """Sync broker account data from broker API"""
    try:
        # Get account info from broker
        account_info = await trading_service.get_account_info(broker_id)
        
        # Update database
        from sqlalchemy import update
        await db.execute(
            update(BrokerAccount)
            .where(BrokerAccount.id == broker_id)
            .values(
                balance=account_info.cash,
                buying_power=account_info.buying_power,
                day_trading_buying_power=account_info.day_trading_buying_power,
                portfolio_value=account_info.portfolio_value,
                last_sync=datetime.utcnow(),
                status=ConnectionStatus.CONNECTED
            )
        )
        await db.commit()
        
        logger.info(f"Broker account data synced: {broker_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to sync broker account data: {str(e)}")
        return False