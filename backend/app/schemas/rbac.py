"""
Pydantic schemas for RBAC (Role-Based Access Control)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class PermissionResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    category: str
    resource: str
    action: str
    is_system_permission: bool
    requires_approval: bool
    
    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: List[str] = Field(default_factory=list)


class RoleCreate(RoleBase):
    parent_role_id: Optional[str] = None
    
    @validator("name")
    def validate_name(cls, v):
        # Role name should be lowercase and contain only letters, numbers, and underscores
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Role name must contain only letters, numbers, underscores, and hyphens")
        return v.lower()


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    
    @validator("name")
    def validate_name(cls, v):
        if v is not None and not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Role name must contain only letters, numbers, underscores, and hyphens")
        return v.lower() if v else v


class RoleResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    display_name: str
    description: Optional[str]
    permissions: List[str]
    is_system_role: bool
    is_active: bool
    parent_role_id: Optional[str]
    level: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class UserPermissionsResponse(BaseModel):
    user_id: str
    email: str
    role_name: Optional[str]
    role_display_name: Optional[str]
    permissions: List[str]


class AuditLogResponse(BaseModel):
    id: str
    organization_id: str
    user_id: Optional[str]
    event_type: str
    event_category: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    status: str
    error_message: Optional[str]
    risk_score: int
    is_suspicious: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PermissionCheckRequest(BaseModel):
    permission: str = Field(..., min_length=1)
    resource_id: Optional[str] = None


class PermissionCheckResponse(BaseModel):
    user_id: str
    permission: str
    resource_id: Optional[str]
    has_permission: bool
    reason: Optional[str] = None


class RolePermissionUpdate(BaseModel):
    permissions: List[str]
    
    @validator("permissions")
    def validate_permissions(cls, v):
        # Basic validation - in real implementation, validate against existing permissions
        for permission in v:
            if not permission or not isinstance(permission, str):
                raise ValueError("All permissions must be non-empty strings")
        return v


class CreatePermissionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    category: str = Field(..., pattern=r"^(portfolio|trading|analytics|admin)$")
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    requires_approval: bool = False
    
    @validator("name")
    def validate_permission_name(cls, v):
        # Permission names should follow pattern: resource.action
        if "." not in v:
            raise ValueError("Permission name must follow format 'resource.action'")
        parts = v.split(".")
        if len(parts) != 2:
            raise ValueError("Permission name must have exactly one dot separator")
        return v.lower()


class AuditLogFilter(BaseModel):
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    resource_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_suspicious: Optional[bool] = None
    min_risk_score: Optional[int] = Field(None, ge=0, le=100)
    
    @validator("end_date")
    def validate_date_range(cls, v, values):
        if v and "start_date" in values and values["start_date"]:
            if v <= values["start_date"]:
                raise ValueError("End date must be after start date")
        return v


class UserRoleAssignment(BaseModel):
    user_id: str
    role_id: str
    assigned_by: str
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    
    @validator("expiry_date")
    def validate_expiry_date(cls, v, values):
        if v and "effective_date" in values and values["effective_date"]:
            if v <= values["effective_date"]:
                raise ValueError("Expiry date must be after effective date")
        return v


class BulkRoleUpdate(BaseModel):
    user_ids: List[str] = Field(..., min_items=1, max_items=100)
    role_id: str
    
    @validator("user_ids")
    def validate_user_ids(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("User IDs must be unique")
        return v


class RoleHierarchy(BaseModel):
    role_id: str
    parent_role_id: Optional[str]
    level: int = Field(0, ge=0, le=10)


class PermissionTemplate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    permissions: List[str] = Field(..., min_items=1)
    role_type: str = Field(..., pattern=r"^(admin|manager|trader|analyst|viewer)$")


class SecurityPolicySettings(BaseModel):
    max_failed_login_attempts: int = Field(5, ge=1, le=20)
    account_lockout_duration: int = Field(30, ge=5, le=1440)  # minutes
    password_expiry_days: int = Field(90, ge=30, le=365)
    require_2fa: bool = False
    session_timeout: int = Field(480, ge=15, le=1440)  # minutes
    ip_whitelist: Optional[List[str]] = None
    allowed_user_agents: Optional[List[str]] = None