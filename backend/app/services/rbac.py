"""
Role-Based Access Control (RBAC) Service
"""

from typing import List, Dict, Any, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import json
from datetime import datetime, timedelta
import uuid

from app.models.organization import Organization, Role, Permission, AuditLog
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings


class RBACService:
    """Role-Based Access Control service for multi-tenant organizations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Permission Management
    async def create_permission(
        self, 
        name: str, 
        display_name: str, 
        description: str,
        category: str, 
        resource: str, 
        action: str
    ) -> Permission:
        """Create a new permission"""
        permission = Permission(
            name=name,
            display_name=display_name,
            description=description,
            category=category,
            resource=resource,
            action=action
        )
        
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission
    
    async def get_permissions(self, category: Optional[str] = None) -> List[Permission]:
        """Get all permissions, optionally filtered by category"""
        query = select(Permission)
        
        if category:
            query = query.where(Permission.category == category)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def initialize_default_permissions(self):
        """Initialize default system permissions"""
        default_permissions = [
            # Portfolio permissions
            ("portfolio.create", "Create Portfolio", "Create new portfolios", "portfolio", "portfolios", "create"),
            ("portfolio.read", "View Portfolio", "View portfolio details", "portfolio", "portfolios", "read"),
            ("portfolio.update", "Update Portfolio", "Modify portfolio settings", "portfolio", "portfolios", "update"),
            ("portfolio.delete", "Delete Portfolio", "Delete portfolios", "portfolio", "portfolios", "delete"),
            ("portfolio.*", "Full Portfolio Access", "Complete portfolio management", "portfolio", "portfolios", "*"),
            
            # Trading permissions
            ("trading.place_order", "Place Orders", "Execute buy/sell orders", "trading", "orders", "create"),
            ("trading.cancel_order", "Cancel Orders", "Cancel pending orders", "trading", "orders", "delete"),
            ("trading.view_orders", "View Orders", "View order history", "trading", "orders", "read"),
            ("trading.modify_order", "Modify Orders", "Modify pending orders", "trading", "orders", "update"),
            ("trading.*", "Full Trading Access", "Complete trading capabilities", "trading", "orders", "*"),
            
            # Analytics permissions
            ("analytics.view_basic", "Basic Analytics", "View basic analytics", "analytics", "reports", "read"),
            ("analytics.view_advanced", "Advanced Analytics", "View advanced analytics", "analytics", "reports", "read"),
            ("analytics.export", "Export Data", "Export analytics data", "analytics", "reports", "export"),
            ("analytics.*", "Full Analytics Access", "Complete analytics access", "analytics", "reports", "*"),
            
            # User management permissions
            ("users.create", "Create Users", "Invite new users", "admin", "users", "create"),
            ("users.read", "View Users", "View user profiles", "admin", "users", "read"),
            ("users.update", "Update Users", "Modify user profiles", "admin", "users", "update"),
            ("users.delete", "Delete Users", "Remove users", "admin", "users", "delete"),
            ("users.*", "Full User Management", "Complete user management", "admin", "users", "*"),
            
            # Organization permissions
            ("org.settings", "Organization Settings", "Manage organization settings", "admin", "organization", "update"),
            ("org.billing", "Billing Management", "Manage billing and subscriptions", "admin", "organization", "billing"),
            ("org.audit", "Audit Access", "View audit logs", "admin", "organization", "audit"),
            
            # System admin permissions
            ("admin.*", "System Administrator", "Full system access", "admin", "system", "*"),
        ]
        
        for name, display_name, description, category, resource, action in default_permissions:
            # Check if permission already exists
            result = await self.db.execute(
                select(Permission).where(Permission.name == name)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                permission = Permission(
                    name=name,
                    display_name=display_name,
                    description=description,
                    category=category,
                    resource=resource,
                    action=action,
                    is_system_permission=True
                )
                self.db.add(permission)
        
        await self.db.commit()
    
    # Role Management
    async def create_role(
        self, 
        organization_id: str, 
        name: str, 
        display_name: str, 
        description: str,
        permissions: List[str],
        created_by: str,
        parent_role_id: Optional[str] = None
    ) -> Role:
        """Create a new role"""
        role = Role(
            organization_id=organization_id,
            name=name,
            display_name=display_name,
            description=description,
            permissions=permissions,
            parent_role_id=parent_role_id,
            created_by=created_by
        )
        
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        
        # Log role creation
        await self.log_audit_event(
            organization_id=organization_id,
            user_id=created_by,
            event_type="role_created",
            event_category="admin",
            action="create_role",
            resource_type="role",
            resource_id=str(role.id),
            details={"role_name": name, "permissions": permissions}
        )
        
        return role
    
    async def update_role(
        self, 
        role_id: str, 
        updates: Dict[str, Any],
        updated_by: str
    ) -> Optional[Role]:
        """Update an existing role"""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()
        
        if not role or role.is_system_role:
            return None
        
        old_values = {
            "name": role.name,
            "display_name": role.display_name,
            "permissions": role.permissions
        }
        
        # Update role fields
        for field, value in updates.items():
            if hasattr(role, field):
                setattr(role, field, value)
        
        await self.db.commit()
        await self.db.refresh(role)
        
        # Log role update
        await self.log_audit_event(
            organization_id=role.organization_id,
            user_id=updated_by,
            event_type="role_updated",
            event_category="admin",
            action="update_role",
            resource_type="role",
            resource_id=str(role.id),
            old_values=old_values,
            new_values=updates
        )
        
        return role
    
    async def get_organization_roles(self, organization_id: str) -> List[Role]:
        """Get all roles for an organization"""
        result = await self.db.execute(
            select(Role)
            .where(Role.organization_id == organization_id)
            .where(Role.is_active == True)
            .order_by(Role.name)
        )
        return result.scalars().all()
    
    async def initialize_default_roles(self, organization_id: str, created_by: str):
        """Initialize default roles for an organization"""
        default_roles = [
            {
                "name": "admin",
                "display_name": "Administrator",
                "description": "Full access to all organization features",
                "permissions": ["admin.*"],
                "is_system_role": True
            },
            {
                "name": "portfolio_manager",
                "display_name": "Portfolio Manager",
                "description": "Manage portfolios and trading strategies",
                "permissions": [
                    "portfolio.*", "trading.*", "analytics.view_advanced", 
                    "analytics.export", "users.read"
                ],
                "is_system_role": True
            },
            {
                "name": "trader",
                "display_name": "Trader",
                "description": "Execute trades and manage assigned portfolios",
                "permissions": [
                    "portfolio.read", "portfolio.update", "trading.*", 
                    "analytics.view_basic", "analytics.view_advanced"
                ],
                "is_system_role": True
            },
            {
                "name": "analyst",
                "display_name": "Analyst",
                "description": "View and analyze portfolio performance",
                "permissions": [
                    "portfolio.read", "trading.view_orders", 
                    "analytics.*"
                ],
                "is_system_role": True
            },
            {
                "name": "viewer",
                "display_name": "Viewer",
                "description": "Read-only access to portfolios and analytics",
                "permissions": [
                    "portfolio.read", "trading.view_orders", "analytics.view_basic"
                ],
                "is_system_role": True
            }
        ]
        
        for role_data in default_roles:
            # Check if role already exists
            result = await self.db.execute(
                select(Role).where(
                    and_(
                        Role.organization_id == organization_id,
                        Role.name == role_data["name"]
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                role = Role(
                    organization_id=organization_id,
                    name=role_data["name"],
                    display_name=role_data["display_name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"],
                    is_system_role=role_data["is_system_role"],
                    created_by=created_by
                )
                self.db.add(role)
        
        await self.db.commit()
    
    # Permission checking
    async def check_permission(
        self, 
        user_id: str, 
        permission: str, 
        organization_id: Optional[str] = None
    ) -> bool:
        """Check if a user has a specific permission"""
        query = select(User).options(selectinload(User.role)).where(User.id == user_id)
        
        if organization_id:
            query = query.where(User.organization_id == organization_id)
        
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user or not user.role:
            return False
        
        return user.has_permission(permission)
    
    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user"""
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.role:
            return set()
        
        return set(user.role.permissions or [])
    
    # Audit logging
    async def log_audit_event(
        self,
        organization_id: str,
        event_type: str,
        event_category: str,
        action: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """Log an audit event"""
        audit_log = AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message
        )
        
        self.db.add(audit_log)
        await self.db.commit()
    
    async def get_audit_logs(
        self, 
        organization_id: str,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Get audit logs with filtering"""
        query = select(AuditLog).where(AuditLog.organization_id == organization_id)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if event_type:
            query = query.where(AuditLog.event_type == event_type)
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # Resource-level permissions
    async def check_resource_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        organization_id: Optional[str] = None
    ) -> bool:
        """Check if user can perform action on specific resource"""
        # First check general permission
        general_permission = f"{resource_type}.{action}"
        if await self.check_permission(user_id, general_permission, organization_id):
            return True
        
        # Check wildcard permission
        wildcard_permission = f"{resource_type}.*"
        if await self.check_permission(user_id, wildcard_permission, organization_id):
            return True
        
        # TODO: Implement resource-specific permissions (e.g., portfolio ownership)
        # This would involve checking if the user owns or has specific access to the resource
        
        return False
    
    # Organization management
    async def get_organization_users(
        self, 
        organization_id: str,
        include_inactive: bool = False
    ) -> List[User]:
        """Get all users in an organization"""
        query = select(User).options(selectinload(User.role)).where(
            User.organization_id == organization_id
        )
        
        if not include_inactive:
            query = query.where(User.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_user_organizations(self, user_id: str) -> List[Organization]:
        """Get all organizations a user belongs to"""
        result = await self.db.execute(
            select(Organization)
            .join(User)
            .where(User.id == user_id)
            .where(Organization.is_active == True)
        )
        return result.scalars().all()


class PermissionDecorator:
    """Decorator for enforcing permissions in API endpoints"""
    
    def __init__(self, permission: str, resource_type: Optional[str] = None):
        self.permission = permission
        self.resource_type = resource_type
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # This would be implemented to work with FastAPI's dependency injection
            # to check permissions before executing the endpoint
            pass
        return wrapper


# Permission checking utilities
def require_permission(permission: str):
    """Decorator to require specific permission"""
    return PermissionDecorator(permission)

def require_resource_permission(resource_type: str, action: str):
    """Decorator to require permission on specific resource type"""
    return PermissionDecorator(f"{resource_type}.{action}", resource_type)