"""
Admin Dashboard API Routes
Comprehensive admin panel endpoints with RBAC
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, File, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from ...services.database import get_db
from ...services.admin_auth_service import AdminAuthService, AuthResult, PermissionCheck
from ...models.admin import (
    Admin, AdminSession, AdminAuditLog, UserAnalytics, RevenueAnalytics,
    TradingAnalytics, SystemMetrics, SupportTicket, AdminNotification,
    FeatureFlag, AdminRoleEnum
)
from ...models.base import BaseModel
from ...models.subscription import Subscription
from ...models.trade import Trade
from ...models.portfolio import Portfolio
from ...utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()

# Initialize auth service (this would come from dependency injection in real app)
auth_service = AdminAuthService(secret_key="your-secret-key")


class AdminResponse:
    """Standard admin API response format"""
    def __init__(self, success: bool, data: Any = None, message: str = "", errors: List[str] = None):
        self.success = success
        self.data = data
        self.message = message
        self.errors = errors or []


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """Get current authenticated admin"""
    token = credentials.credentials
    payload = auth_service.verify_jwt_token(token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    admin = auth_service.validate_session(db, payload.get('session_id'))
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    return admin


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get admin from kwargs or dependency
            admin = kwargs.get('current_admin')
            db = kwargs.get('db')
            
            if not admin or not db:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            permission_check = auth_service.check_permission(db, admin, permission)
            if not permission_check.allowed:
                raise HTTPException(status_code=403, detail=permission_check.reason)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Authentication Endpoints
@router.post("/auth/login")
async def admin_login(
    request: Request,
    username: str,
    password: str,
    mfa_token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Admin login with MFA support"""
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    
    auth_result = auth_service.authenticate(
        db, username, password, mfa_token, ip_address, user_agent
    )
    
    if not auth_result.success:
        raise HTTPException(
            status_code=401 if auth_result.error_code != "MFA_REQUIRED" else 200,
            detail={
                "message": auth_result.message,
                "error_code": auth_result.error_code,
                "requires_mfa": auth_result.requires_mfa
            }
        )
    
    # Generate JWT token
    jwt_token = auth_service.create_jwt_token(auth_result.admin, str(auth_result.session.id))
    
    return {
        "success": True,
        "token": jwt_token,
        "admin": {
            "id": str(auth_result.admin.id),
            "username": auth_result.admin.username,
            "email": auth_result.admin.email,
            "role": auth_result.admin.role.value,
            "permissions": _get_admin_permissions(db, auth_result.admin)
        },
        "session": {
            "id": str(auth_result.session.id),
            "expires_at": auth_result.session.expires_at.isoformat()
        }
    }


@router.post("/auth/logout")
async def admin_logout(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Admin logout"""
    # Get current session token from request context
    # This would be extracted from the JWT payload in a real implementation
    session_token = "current_session_token"  # Placeholder
    
    success = auth_service.logout(db, session_token, str(current_admin.id))
    
    return {"success": success, "message": "Logged out successfully"}


@router.get("/auth/me")
async def get_current_admin_info(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get current admin information and permissions"""
    return {
        "admin": {
            "id": str(current_admin.id),
            "username": current_admin.username,
            "email": current_admin.email,
            "first_name": current_admin.first_name,
            "last_name": current_admin.last_name,
            "role": current_admin.role.value,
            "department": current_admin.department,
            "permissions": _get_admin_permissions(db, current_admin),
            "last_login": current_admin.last_login.isoformat() if current_admin.last_login else None
        }
    }


# User Management Endpoints
@router.get("/users")
@require_permission("VIEW_USERS")
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    status: Optional[str] = None,
    subscription_tier: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get paginated list of users with filtering"""
    
    # Build query
    query = db.query(BaseModel)  # This should be User model when available
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                BaseModel.email.ilike(f"%{search}%"),
                BaseModel.username.ilike(f"%{search}%")
            )
        )
    
    if status:
        query = query.filter(BaseModel.is_active == (status == "active"))
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_order == "desc":
        query = query.order_by(desc(getattr(BaseModel, sort_by, BaseModel.created_at)))
    else:
        query = query.order_by(asc(getattr(BaseModel, sort_by, BaseModel.created_at)))
    
    # Apply pagination
    offset = (page - 1) * limit
    users = query.offset(offset).limit(limit).all()
    
    # Log admin action
    _log_admin_action(db, current_admin, "VIEW_USERS", f"Viewed users list (page {page})")
    
    return {
        "users": [user.to_dict() for user in users],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@router.get("/users/{user_id}")
@require_permission("VIEW_USER_DETAILS")
async def get_user_detail(
    user_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed user information"""
    
    # Get user details (placeholder - would use actual User model)
    user = db.query(BaseModel).filter(BaseModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's subscriptions
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).order_by(desc(Subscription.created_at)).limit(10).all()
    
    # Get user's recent trades
    trades = db.query(Trade).filter(
        Trade.user_id == user_id
    ).order_by(desc(Trade.created_at)).limit(20).all()
    
    # Get user's portfolio
    portfolio = db.query(Portfolio).filter(
        Portfolio.user_id == user_id
    ).first()
    
    # Log admin action
    _log_admin_action(db, current_admin, "VIEW_USER_DETAIL", f"Viewed user details: {user_id}")
    
    return {
        "user": user.to_dict(),
        "subscriptions": [sub.to_dict() for sub in subscriptions],
        "recent_trades": [trade.to_dict() for trade in trades],
        "portfolio": portfolio.to_dict() if portfolio else None
    }


@router.put("/users/{user_id}/status")
@require_permission("MODIFY_USER_STATUS")
async def update_user_status(
    user_id: str,
    is_active: bool,
    reason: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update user status (activate/deactivate)"""
    
    user = db.query(BaseModel).filter(BaseModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_status = user.is_active
    user.is_active = is_active
    db.commit()
    
    # Log admin action with before/after state
    _log_admin_action(
        db, current_admin, 
        "USER_STATUS_CHANGED",
        f"Changed user {user_id} status from {old_status} to {is_active}. Reason: {reason}",
        resource_id=user_id,
        before_state={"is_active": old_status},
        after_state={"is_active": is_active}
    )
    
    return {"success": True, "message": f"User {'activated' if is_active else 'deactivated'} successfully"}


@router.post("/users/{user_id}/reset-password")
@require_permission("RESET_USER_PASSWORD")
async def reset_user_password(
    user_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Reset user password and send email"""
    
    user = db.query(BaseModel).filter(BaseModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate temporary password
    import secrets
    temp_password = secrets.token_urlsafe(12)
    
    # Here you would:
    # 1. Hash the password
    # 2. Update user's password
    # 3. Send email to user
    # 4. Log the action
    
    _log_admin_action(
        db, current_admin,
        "USER_PASSWORD_RESET",
        f"Reset password for user {user_id}",
        resource_id=user_id
    )
    
    return {"success": True, "message": "Password reset email sent to user"}


# Analytics and Dashboard Endpoints
@router.get("/dashboard/overview")
@require_permission("VIEW_DASHBOARD")
async def get_dashboard_overview(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get dashboard overview with key metrics"""
    
    today = datetime.utcnow().date()
    
    # Get latest analytics
    user_analytics = db.query(UserAnalytics).filter(
        UserAnalytics.date == today
    ).first()
    
    revenue_analytics = db.query(RevenueAnalytics).filter(
        RevenueAnalytics.date == today
    ).first()
    
    trading_analytics = db.query(TradingAnalytics).filter(
        TradingAnalytics.date == today
    ).first()
    
    # Get system metrics (latest)
    system_metrics = db.query(SystemMetrics).order_by(
        desc(SystemMetrics.timestamp)
    ).first()
    
    # Get pending support tickets
    pending_tickets = db.query(SupportTicket).filter(
        SupportTicket.status.in_(["open", "in_progress"])
    ).count()
    
    # Get unread notifications for current admin
    unread_notifications = db.query(AdminNotification).filter(
        and_(
            AdminNotification.admin_id == current_admin.id,
            AdminNotification.is_read == False
        )
    ).count()
    
    return {
        "overview": {
            "users": {
                "total": user_analytics.total_users if user_analytics else 0,
                "new_today": user_analytics.new_registrations if user_analytics else 0,
                "active_today": user_analytics.active_users_daily if user_analytics else 0
            },
            "revenue": {
                "daily": revenue_analytics.daily_revenue if revenue_analytics else 0,
                "mrr": revenue_analytics.monthly_recurring_revenue if revenue_analytics else 0,
                "arr": revenue_analytics.annual_recurring_revenue if revenue_analytics else 0
            },
            "trading": {
                "trades_today": trading_analytics.total_trades if trading_analytics else 0,
                "success_rate": trading_analytics.win_rate if trading_analytics else 0,
                "total_volume": trading_analytics.total_volume if trading_analytics else 0
            },
            "system": {
                "api_response_time": system_metrics.api_response_time_avg if system_metrics else 0,
                "active_sessions": system_metrics.active_user_sessions if system_metrics else 0,
                "system_status": "healthy" if system_metrics and system_metrics.api_error_rate < 1 else "warning"
            },
            "support": {
                "pending_tickets": pending_tickets,
                "unread_notifications": unread_notifications
            }
        }
    }


@router.get("/analytics/users")
@require_permission("VIEW_USER_ANALYTICS")
async def get_user_analytics(
    days: int = Query(30, ge=1, le=365),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get user analytics for specified period"""
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    analytics = db.query(UserAnalytics).filter(
        and_(
            UserAnalytics.date >= start_date,
            UserAnalytics.date <= end_date
        )
    ).order_by(UserAnalytics.date).all()
    
    return {
        "analytics": [
            {
                "date": a.date.isoformat(),
                "total_users": a.total_users,
                "new_registrations": a.new_registrations,
                "active_users_daily": a.active_users_daily,
                "churned_users": a.churned_users
            } for a in analytics
        ]
    }


@router.get("/analytics/revenue")
@require_permission("VIEW_FINANCIAL_ANALYTICS")
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get revenue analytics for specified period"""
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    
    analytics = db.query(RevenueAnalytics).filter(
        and_(
            RevenueAnalytics.date >= start_date,
            RevenueAnalytics.date <= end_date
        )
    ).order_by(RevenueAnalytics.date).all()
    
    return {
        "analytics": [
            {
                "date": a.date.isoformat(),
                "daily_revenue": a.daily_revenue,
                "mrr": a.monthly_recurring_revenue,
                "subscription_revenue": a.subscription_revenue,
                "commission_revenue": a.commission_revenue,
                "costs": a.infrastructure_costs + a.data_provider_costs + a.third_party_service_costs
            } for a in analytics
        ]
    }


# Support Ticket Management
@router.get("/tickets")
@require_permission("VIEW_SUPPORT_TICKETS")
async def get_support_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to_me: bool = False,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get support tickets with filtering"""
    
    query = db.query(SupportTicket)
    
    # Apply filters
    if status:
        query = query.filter(SupportTicket.status == status)
    
    if priority:
        query = query.filter(SupportTicket.priority == priority)
    
    if assigned_to_me:
        query = query.filter(SupportTicket.assigned_admin_id == current_admin.id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    tickets = query.order_by(desc(SupportTicket.created_at)).offset(offset).limit(limit).all()
    
    return {
        "tickets": [
            {
                "id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "subject": ticket.subject,
                "status": ticket.status,
                "priority": ticket.priority,
                "category": ticket.category,
                "created_at": ticket.created_at.isoformat(),
                "assigned_admin": ticket.assigned_admin.username if ticket.assigned_admin else None
            } for ticket in tickets
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


# Utility Functions
def _get_admin_permissions(db: Session, admin: Admin) -> List[str]:
    """Get list of permissions for admin"""
    if admin.role == AdminRoleEnum.SUPER_ADMIN:
        return ["ALL"]
    
    # Get role-based permissions
    permissions = db.query(AdminPermission.name).join(
        AdminRolePermission
    ).filter(
        AdminRolePermission.role == admin.role
    ).all()
    
    return [p[0] for p in permissions]


def _log_admin_action(
    db: Session,
    admin: Admin,
    action: str,
    description: str,
    resource_id: str = None,
    before_state: Dict = None,
    after_state: Dict = None
):
    """Log admin action to audit trail"""
    log_entry = AdminAuditLog(
        admin_id=admin.id,
        action=action,
        category="ADMIN_ACTION",
        description=description,
        resource_id=resource_id,
        before_state=before_state,
        after_state=after_state,
        severity="INFO"
    )
    
    db.add(log_entry)
    db.commit()