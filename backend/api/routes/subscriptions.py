from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from services.database import get_db
from models.subscription import SubscriptionPlan, Subscription
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class PlanResponse(BaseModel):
    plan_id: str
    name: str
    description: Optional[str]
    price: float
    currency: str
    interval: str
    features: List[str]
    max_watchlists: int
    max_positions: int
    automated_trading: bool
    backtesting: bool
    advanced_analytics: bool
    api_access: bool
    priority_support: bool

@router.get("/plans", response_model=List[PlanResponse])
async def get_subscription_plans(db: AsyncSession = Depends(get_db)):
    """Get all available subscription plans"""
    try:
        result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.is_active == True))
        plans = result.scalars().all()
        
        return [
            PlanResponse(
                plan_id=plan.plan_id,
                name=plan.name,
                description=plan.description,
                price=plan.price,
                currency=plan.currency,
                interval=plan.interval.value,
                features=plan.features.split(",") if plan.features else [],
                max_watchlists=plan.max_watchlists,
                max_positions=plan.max_positions,
                automated_trading=plan.automated_trading,
                backtesting=plan.backtesting,
                advanced_analytics=plan.advanced_analytics,
                api_access=plan.api_access,
                priority_support=plan.priority_support
            )
            for plan in plans
        ]
        
    except Exception as e:
        logger.error(f"Failed to get subscription plans: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription plans"
        )

@router.post("/subscribe")
async def subscribe_to_plan(db: AsyncSession = Depends(get_db)):
    """Subscribe to a plan - placeholder implementation"""
    # TODO: Implement Stripe integration
    return {"message": "Subscription functionality coming soon"}

@router.get("/current")
async def get_current_subscription(db: AsyncSession = Depends(get_db)):
    """Get current user subscription - placeholder implementation"""
    # TODO: Implement subscription retrieval
    return {"message": "Subscription retrieval coming soon"}