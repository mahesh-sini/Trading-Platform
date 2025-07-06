"""
Admin Subscription Management API
Comprehensive subscription and billing management for admins
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from ...services.database import get_db
from ...models.admin import Admin, AdminAuditLog
from ...models.subscription import Subscription, SubscriptionPlan, Payment, Refund
from ...models.base import BaseModel  # User model placeholder
from ...utils.logging_config import get_logger
from .admin import get_current_admin, require_permission, _log_admin_action

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/subscriptions", tags=["admin-subscriptions"])


# Subscription Plan Management
@router.get("/plans")
@require_permission("VIEW_SUBSCRIPTION_PLANS")
async def get_subscription_plans(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all subscription plans"""
    
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.price).all()
    
    return {
        "plans": [
            {
                "id": str(plan.id),
                "name": plan.name,
                "description": plan.description,
                "price": float(plan.price),
                "currency": plan.currency,
                "billing_cycle": plan.billing_cycle,
                "features": plan.features,
                "limits": plan.limits,
                "is_active": plan.is_active,
                "trial_days": plan.trial_days,
                "auto_trading_limit": plan.auto_trading_limit,
                "api_calls_limit": plan.api_calls_limit
            } for plan in plans
        ]
    }


@router.post("/plans")
@require_permission("CREATE_SUBSCRIPTION_PLAN")
async def create_subscription_plan(
    plan_data: Dict[str, Any],
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create new subscription plan"""
    
    # Validate required fields
    required_fields = ["name", "price", "currency", "billing_cycle"]
    for field in required_fields:
        if field not in plan_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Create subscription plan
    plan = SubscriptionPlan(
        name=plan_data["name"],
        description=plan_data.get("description", ""),
        price=Decimal(str(plan_data["price"])),
        currency=plan_data["currency"],
        billing_cycle=plan_data["billing_cycle"],
        features=plan_data.get("features", {}),
        limits=plan_data.get("limits", {}),
        trial_days=plan_data.get("trial_days", 0),
        auto_trading_limit=plan_data.get("auto_trading_limit", 0),
        api_calls_limit=plan_data.get("api_calls_limit", 1000),
        is_active=plan_data.get("is_active", True)
    )
    
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    _log_admin_action(
        db, current_admin,
        "SUBSCRIPTION_PLAN_CREATED",
        f"Created subscription plan: {plan.name}",
        resource_id=str(plan.id),
        after_state=plan_data
    )
    
    return {
        "success": True,
        "message": "Subscription plan created successfully",
        "plan_id": str(plan.id)
    }


@router.put("/plans/{plan_id}")
@require_permission("MODIFY_SUBSCRIPTION_PLAN")
async def update_subscription_plan(
    plan_id: str,
    plan_data: Dict[str, Any],
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update subscription plan"""
    
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    
    # Store old state for audit
    old_state = {
        "name": plan.name,
        "price": float(plan.price),
        "features": plan.features,
        "limits": plan.limits,
        "is_active": plan.is_active
    }
    
    # Update fields
    updateable_fields = [
        "name", "description", "price", "features", "limits", 
        "trial_days", "auto_trading_limit", "api_calls_limit", "is_active"
    ]
    
    for field in updateable_fields:
        if field in plan_data:
            if field == "price":
                setattr(plan, field, Decimal(str(plan_data[field])))
            else:
                setattr(plan, field, plan_data[field])
    
    db.commit()
    
    _log_admin_action(
        db, current_admin,
        "SUBSCRIPTION_PLAN_UPDATED",
        f"Updated subscription plan: {plan.name}",
        resource_id=plan_id,
        before_state=old_state,
        after_state=plan_data
    )
    
    return {"success": True, "message": "Subscription plan updated successfully"}


# User Subscription Management
@router.get("/users")
@require_permission("VIEW_USER_SUBSCRIPTIONS")
async def get_user_subscriptions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    plan_name: Optional[str] = None,
    status: Optional[str] = None,
    billing_cycle: Optional[str] = None,
    expires_within_days: Optional[int] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get user subscriptions with filtering"""
    
    # Build query with joins
    query = db.query(Subscription).join(SubscriptionPlan)
    
    # Apply filters
    if search:
        # Join with User table when available
        query = query.filter(
            or_(
                BaseModel.email.ilike(f"%{search}%"),
                BaseModel.username.ilike(f"%{search}%")
            )
        )
    
    if plan_name:
        query = query.filter(SubscriptionPlan.name == plan_name)
    
    if status:
        query = query.filter(Subscription.status == status)
    
    if billing_cycle:
        query = query.filter(SubscriptionPlan.billing_cycle == billing_cycle)
    
    if expires_within_days:
        expiry_date = datetime.utcnow() + timedelta(days=expires_within_days)
        query = query.filter(
            and_(
                Subscription.status == "active",
                Subscription.expires_at <= expiry_date
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    subscriptions = query.order_by(desc(Subscription.created_at)).offset(offset).limit(limit).all()
    
    return {
        "subscriptions": [
            {
                "id": str(sub.id),
                "user_id": str(sub.user_id),
                "user_email": "user@example.com",  # Would come from joined User table
                "plan_name": sub.plan.name,
                "status": sub.status,
                "billing_cycle": sub.plan.billing_cycle,
                "price": float(sub.plan.price),
                "currency": sub.plan.currency,
                "started_at": sub.started_at.isoformat(),
                "expires_at": sub.expires_at.isoformat(),
                "auto_renew": sub.auto_renew,
                "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                "usage_stats": sub.usage_stats
            } for sub in subscriptions
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@router.get("/users/{user_id}")
@require_permission("VIEW_USER_SUBSCRIPTION_DETAILS")
async def get_user_subscription_detail(
    user_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed subscription information for a user"""
    
    # Get current subscription
    current_subscription = db.query(Subscription).filter(
        and_(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trial", "past_due"])
        )
    ).first()
    
    # Get subscription history
    subscription_history = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).order_by(desc(Subscription.created_at)).limit(10).all()
    
    # Get payment history
    payment_history = db.query(Payment).filter(
        Payment.user_id == user_id
    ).order_by(desc(Payment.created_at)).limit(20).all()
    
    # Get refund history
    refund_history = db.query(Refund).filter(
        Refund.user_id == user_id
    ).order_by(desc(Refund.created_at)).all()
    
    # Calculate subscription metrics
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.user_id == user_id,
            Payment.status == "completed"
        )
    ).scalar() or 0
    
    total_refunds = db.query(func.sum(Refund.amount)).filter(
        Refund.user_id == user_id
    ).scalar() or 0
    
    _log_admin_action(
        db, current_admin,
        "VIEW_USER_SUBSCRIPTION_DETAIL",
        f"Viewed subscription details for user: {user_id}",
        resource_id=user_id
    )
    
    return {
        "current_subscription": {
            "id": str(current_subscription.id),
            "plan_name": current_subscription.plan.name,
            "status": current_subscription.status,
            "price": float(current_subscription.plan.price),
            "currency": current_subscription.plan.currency,
            "started_at": current_subscription.started_at.isoformat(),
            "expires_at": current_subscription.expires_at.isoformat(),
            "auto_renew": current_subscription.auto_renew,
            "trial_ends_at": current_subscription.trial_ends_at.isoformat() if current_subscription.trial_ends_at else None,
            "usage_stats": current_subscription.usage_stats
        } if current_subscription else None,
        "subscription_history": [
            {
                "id": str(sub.id),
                "plan_name": sub.plan.name,
                "status": sub.status,
                "started_at": sub.started_at.isoformat(),
                "expires_at": sub.expires_at.isoformat(),
                "cancelled_at": sub.cancelled_at.isoformat() if sub.cancelled_at else None
            } for sub in subscription_history
        ],
        "payment_history": [
            {
                "id": str(payment.id),
                "amount": float(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "payment_method": payment.payment_method,
                "created_at": payment.created_at.isoformat(),
                "description": payment.description
            } for payment in payment_history
        ],
        "refund_history": [
            {
                "id": str(refund.id),
                "amount": float(refund.amount),
                "reason": refund.reason,
                "status": refund.status,
                "created_at": refund.created_at.isoformat(),
                "processed_by": refund.processed_by_admin.username if refund.processed_by_admin else None
            } for refund in refund_history
        ],
        "metrics": {
            "total_revenue": float(total_revenue),
            "total_refunds": float(total_refunds),
            "net_revenue": float(total_revenue - total_refunds),
            "subscription_count": len(subscription_history)
        }
    }


@router.post("/users/{user_id}/change-plan")
@require_permission("CHANGE_USER_SUBSCRIPTION")
async def change_user_subscription_plan(
    user_id: str,
    new_plan_id: str,
    reason: str,
    apply_immediately: bool = True,
    prorate: bool = True,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Change user's subscription plan"""
    
    # Get current subscription
    current_subscription = db.query(Subscription).filter(
        and_(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        )
    ).first()
    
    if not current_subscription:
        raise HTTPException(status_code=404, detail="No active subscription found for user")
    
    # Get new plan
    new_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == new_plan_id).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="New subscription plan not found")
    
    old_plan_name = current_subscription.plan.name
    
    if apply_immediately:
        # Calculate proration if needed
        proration_credit = 0
        if prorate and current_subscription.expires_at > datetime.utcnow():
            days_remaining = (current_subscription.expires_at - datetime.utcnow()).days
            if current_subscription.plan.billing_cycle == "monthly":
                daily_rate = float(current_subscription.plan.price) / 30
            else:  # yearly
                daily_rate = float(current_subscription.plan.price) / 365
            proration_credit = daily_rate * days_remaining
        
        # Update current subscription
        current_subscription.status = "cancelled"
        current_subscription.cancelled_at = datetime.utcnow()
        
        # Create new subscription
        new_subscription = Subscription(
            user_id=user_id,
            plan_id=new_plan_id,
            status="active",
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(
                days=30 if new_plan.billing_cycle == "monthly" else 365
            ),
            auto_renew=current_subscription.auto_renew
        )
        
        db.add(new_subscription)
        db.commit()
        
        _log_admin_action(
            db, current_admin,
            "USER_SUBSCRIPTION_CHANGED",
            f"Changed user {user_id} subscription from {old_plan_name} to {new_plan.name}. Reason: {reason}",
            resource_id=user_id,
            before_state={"plan": old_plan_name, "status": "active"},
            after_state={"plan": new_plan.name, "proration_credit": proration_credit}
        )
        
        return {
            "success": True,
            "message": f"Subscription changed from {old_plan_name} to {new_plan.name}",
            "proration_credit": proration_credit,
            "new_subscription_id": str(new_subscription.id)
        }
    else:
        # Schedule change for next billing cycle
        current_subscription.next_plan_id = new_plan_id
        db.commit()
        
        _log_admin_action(
            db, current_admin,
            "USER_SUBSCRIPTION_CHANGE_SCHEDULED",
            f"Scheduled subscription change for user {user_id} from {old_plan_name} to {new_plan.name}",
            resource_id=user_id
        )
        
        return {
            "success": True,
            "message": f"Subscription change scheduled for next billing cycle",
            "effective_date": current_subscription.expires_at.isoformat()
        }


@router.post("/users/{user_id}/cancel")
@require_permission("CANCEL_USER_SUBSCRIPTION")
async def cancel_user_subscription(
    user_id: str,
    reason: str,
    immediate: bool = False,
    refund_amount: Optional[float] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cancel user subscription"""
    
    subscription = db.query(Subscription).filter(
        and_(
            Subscription.user_id == user_id,
            Subscription.status == "active"
        )
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    if immediate:
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.utcnow()
        subscription.expires_at = datetime.utcnow()
    else:
        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.utcnow()
        # Keep expires_at as is for end-of-period cancellation
    
    # Process refund if specified
    refund_id = None
    if refund_amount and refund_amount > 0:
        if current_admin.refund_approval_limit < refund_amount:
            raise HTTPException(
                status_code=403,
                detail=f"Refund amount exceeds your approval limit of ${current_admin.refund_approval_limit}"
            )
        
        refund = Refund(
            user_id=user_id,
            subscription_id=subscription.id,
            amount=Decimal(str(refund_amount)),
            currency=subscription.plan.currency,
            reason=reason,
            status="pending",
            processed_by=current_admin.id
        )
        
        db.add(refund)
        db.commit()
        db.refresh(refund)
        refund_id = str(refund.id)
    
    db.commit()
    
    _log_admin_action(
        db, current_admin,
        "USER_SUBSCRIPTION_CANCELLED",
        f"Cancelled subscription for user {user_id}. Reason: {reason}",
        resource_id=user_id,
        after_state={
            "immediate": immediate,
            "refund_amount": refund_amount,
            "refund_id": refund_id
        }
    )
    
    return {
        "success": True,
        "message": f"Subscription {'immediately cancelled' if immediate else 'cancelled at end of period'}",
        "refund_id": refund_id
    }


# Payment and Billing Management
@router.get("/payments")
@require_permission("VIEW_PAYMENTS")
async def get_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get payments with filtering"""
    
    query = db.query(Payment)
    
    # Apply filters
    if status:
        query = query.filter(Payment.status == status)
    
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    
    if date_from:
        query = query.filter(Payment.created_at >= date_from)
    
    if date_to:
        query = query.filter(Payment.created_at <= date_to)
    
    if min_amount:
        query = query.filter(Payment.amount >= min_amount)
    
    if max_amount:
        query = query.filter(Payment.amount <= max_amount)
    
    # Get total count and sum
    total = query.count()
    total_amount = query.filter(Payment.status == "completed").with_entities(
        func.sum(Payment.amount)
    ).scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * limit
    payments = query.order_by(desc(Payment.created_at)).offset(offset).limit(limit).all()
    
    return {
        "payments": [
            {
                "id": str(payment.id),
                "user_id": str(payment.user_id),
                "amount": float(payment.amount),
                "currency": payment.currency,
                "status": payment.status,
                "payment_method": payment.payment_method,
                "transaction_id": payment.transaction_id,
                "created_at": payment.created_at.isoformat(),
                "description": payment.description,
                "failure_reason": payment.failure_reason
            } for payment in payments
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "summary": {
            "total_amount": float(total_amount),
            "total_count": total
        }
    }


@router.get("/refunds")
@require_permission("VIEW_REFUNDS")
async def get_refunds(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get refunds with filtering"""
    
    query = db.query(Refund)
    
    if status:
        query = query.filter(Refund.status == status)
    
    total = query.count()
    total_amount = query.with_entities(func.sum(Refund.amount)).scalar() or 0
    
    offset = (page - 1) * limit
    refunds = query.order_by(desc(Refund.created_at)).offset(offset).limit(limit).all()
    
    return {
        "refunds": [
            {
                "id": str(refund.id),
                "user_id": str(refund.user_id),
                "amount": float(refund.amount),
                "currency": refund.currency,
                "reason": refund.reason,
                "status": refund.status,
                "created_at": refund.created_at.isoformat(),
                "processed_by": refund.processed_by_admin.username if refund.processed_by_admin else None
            } for refund in refunds
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "summary": {
            "total_amount": float(total_amount),
            "total_count": total
        }
    }


@router.post("/refunds/{refund_id}/process")
@require_permission("PROCESS_REFUNDS")
async def process_refund(
    refund_id: str,
    action: str,  # "approve" or "reject"
    notes: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Process pending refund"""
    
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        raise HTTPException(status_code=404, detail="Refund not found")
    
    if refund.status != "pending":
        raise HTTPException(status_code=400, detail="Refund is not in pending status")
    
    # Check approval limits
    if action == "approve" and current_admin.refund_approval_limit < float(refund.amount):
        raise HTTPException(
            status_code=403,
            detail=f"Refund amount exceeds your approval limit of ${current_admin.refund_approval_limit}"
        )
    
    if action == "approve":
        refund.status = "approved"
        # Here you would integrate with payment processor to process the refund
        refund.processed_at = datetime.utcnow()
    elif action == "reject":
        refund.status = "rejected"
        refund.processed_at = datetime.utcnow()
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
    
    if notes:
        refund.admin_notes = notes
    
    refund.processed_by = current_admin.id
    db.commit()
    
    _log_admin_action(
        db, current_admin,
        f"REFUND_{action.upper()}",
        f"{action.title()} refund {refund_id} for ${refund.amount}",
        resource_id=refund_id,
        after_state={"action": action, "notes": notes}
    )
    
    return {
        "success": True,
        "message": f"Refund {action}d successfully"
    }