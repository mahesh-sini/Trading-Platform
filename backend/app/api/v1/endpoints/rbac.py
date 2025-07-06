"""
Role-Based Access Control (RBAC) API endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Role, Permission, AuditLog
from app.services.rbac import RBACService
from app.schemas.rbac import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionResponse,
    AuditLogResponse,
    UserPermissionsResponse
)

router = APIRouter()


# Permissions
@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(None)
):
    """List all available permissions"""
    # Check if user can view permissions
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.read", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    permissions = await rbac_service.get_permissions(category)
    return [PermissionResponse.from_orm(perm) for perm in permissions]


@router.get("/permissions/categories")
async def get_permission_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all permission categories"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.read", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Return predefined categories
    categories = [
        {"name": "portfolio", "display_name": "Portfolio Management"},
        {"name": "trading", "display_name": "Trading"},
        {"name": "analytics", "display_name": "Analytics & Reporting"},
        {"name": "admin", "display_name": "Administration"}
    ]
    
    return categories


# Roles
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new role"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.create", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create roles"
        )
    
    role = await rbac_service.create_role(
        organization_id=str(current_user.organization_id),
        name=role_data.name,
        display_name=role_data.display_name,
        description=role_data.description,
        permissions=role_data.permissions,
        created_by=str(current_user.id),
        parent_role_id=role_data.parent_role_id
    )
    
    return RoleResponse.from_orm(role)


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all roles in the organization"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.read", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    roles = await rbac_service.get_organization_roles(str(current_user.organization_id))
    return [RoleResponse.from_orm(role) for role in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get role by ID"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.read", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    role = await db.get(Role, role_id)
    if not role or role.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return RoleResponse.from_orm(role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a role"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.update", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update roles"
        )
    
    role = await rbac_service.update_role(
        role_id,
        role_update.dict(exclude_unset=True),
        str(current_user.id)
    )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found or cannot be updated"
        )
    
    return RoleResponse.from_orm(role)


@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a role"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.delete", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete roles"
        )
    
    role = await db.get(Role, role_id)
    if not role or role.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )
    
    # Check if role is in use
    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete role that is assigned to users"
        )
    
    role.is_active = False
    await db.commit()
    
    # Log audit event
    await rbac_service.log_audit_event(
        organization_id=str(current_user.organization_id),
        user_id=str(current_user.id),
        event_type="role_deleted",
        event_category="admin",
        action="delete_role",
        resource_type="role",
        resource_id=role_id,
        details={"role_name": role.name}
    )
    
    return {"message": "Role deleted successfully"}


# User permissions
@router.get("/users/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all permissions for a user"""
    # Check permission or if user is checking their own permissions
    rbac_service = RBACService(db)
    if (user_id != str(current_user.id) and 
        not await rbac_service.check_permission(
            str(current_user.id), "users.read", str(current_user.organization_id)
        )):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    permissions = await rbac_service.get_user_permissions(user_id)
    
    # Get user details
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserPermissionsResponse(
        user_id=user_id,
        email=user.email,
        role_name=user.role.name if user.role else None,
        role_display_name=user.role.display_name if user.role else None,
        permissions=list(permissions)
    )


@router.post("/users/{user_id}/check-permission")
async def check_user_permission(
    user_id: str,
    permission_check: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if a user has a specific permission"""
    # Check permission or if user is checking their own permissions
    rbac_service = RBACService(db)
    if (user_id != str(current_user.id) and 
        not await rbac_service.check_permission(
            str(current_user.id), "users.read", str(current_user.organization_id)
        )):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    permission = permission_check.get("permission")
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permission parameter is required"
        )
    
    has_permission = await rbac_service.check_permission(
        user_id, permission, str(current_user.organization_id)
    )
    
    return {
        "user_id": user_id,
        "permission": permission,
        "has_permission": has_permission
    }


# Audit logs
@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get audit logs"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "org.audit", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view audit logs"
        )
    
    audit_logs = await rbac_service.get_audit_logs(
        organization_id=str(current_user.organization_id),
        user_id=user_id,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return [AuditLogResponse.from_orm(log) for log in audit_logs]


@router.get("/audit-logs/events")
async def get_audit_event_types(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all audit event types"""
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "org.audit", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Return common event types
    event_types = [
        {"name": "user_login", "display_name": "User Login"},
        {"name": "user_logout", "display_name": "User Logout"},
        {"name": "user_created", "display_name": "User Created"},
        {"name": "user_updated", "display_name": "User Updated"},
        {"name": "user_deleted", "display_name": "User Deleted"},
        {"name": "role_created", "display_name": "Role Created"},
        {"name": "role_updated", "display_name": "Role Updated"},
        {"name": "role_deleted", "display_name": "Role Deleted"},
        {"name": "permission_granted", "display_name": "Permission Granted"},
        {"name": "permission_revoked", "display_name": "Permission Revoked"},
        {"name": "organization_updated", "display_name": "Organization Updated"},
        {"name": "settings_updated", "display_name": "Settings Updated"},
        {"name": "trade_executed", "display_name": "Trade Executed"},
        {"name": "order_placed", "display_name": "Order Placed"},
        {"name": "order_cancelled", "display_name": "Order Cancelled"},
    ]
    
    return event_types


# Current user's permissions and role
@router.get("/me/permissions", response_model=UserPermissionsResponse)
async def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's permissions"""
    rbac_service = RBACService(db)
    permissions = await rbac_service.get_user_permissions(str(current_user.id))
    
    return UserPermissionsResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        role_name=current_user.role.name if current_user.role else None,
        role_display_name=current_user.role.display_name if current_user.role else None,
        permissions=list(permissions)
    )


@router.get("/me/role", response_model=RoleResponse)
async def get_my_role(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's role"""
    if not current_user.role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No role assigned"
        )
    
    return RoleResponse.from_orm(current_user.role)