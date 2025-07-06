"""
Pydantic schemas for organization management
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import re


class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class OrganizationCreate(OrganizationBase):
    subscription_tier: str = Field("free", pattern=r"^(free|basic|pro|enterprise)$")
    settings: Optional[Dict[str, Any]] = None
    
    @validator("slug")
    def validate_slug(cls, v):
        if not re.match(r"^[a-z0-9-]+$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    display_name: str
    slug: str
    description: Optional[str]
    subscription_tier: str
    subscription_status: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class OrganizationSettingsUpdate(BaseModel):
    # Trading settings
    trading_enabled: Optional[bool] = None
    paper_trading_only: Optional[bool] = None
    max_portfolio_value: Optional[int] = None
    max_daily_trades: Optional[int] = None
    allowed_symbols: Optional[List[str]] = None
    blocked_symbols: Optional[List[str]] = None
    
    # Risk management
    risk_limits: Optional[Dict[str, Any]] = None
    margin_enabled: Optional[bool] = None
    margin_ratio: Optional[int] = Field(None, ge=0, le=100)
    
    # Data and analytics
    data_retention_days: Optional[int] = Field(None, ge=30, le=3650)
    analytics_enabled: Optional[bool] = None
    external_data_enabled: Optional[bool] = None
    
    # API and integrations
    api_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None
    webhook_urls: Optional[List[str]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    
    # Compliance and audit
    audit_level: Optional[str] = Field(None, pattern=r"^(minimal|standard|comprehensive)$")
    compliance_mode: Optional[str] = Field(None, pattern=r"^(standard|strict|custom)$")
    data_export_enabled: Optional[bool] = None
    
    # UI/UX preferences
    theme: Optional[str] = Field(None, pattern=r"^(light|dark|auto)$")
    default_dashboard: Optional[str] = None
    custom_branding: Optional[Dict[str, Any]] = None


class UserInvitationCreate(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    role_id: str
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    message: Optional[str] = Field(None, max_length=500)


class UserInvitationResponse(BaseModel):
    id: str
    organization_id: str
    role_id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    status: str
    expires_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class OrganizationStatsResponse(BaseModel):
    total_users: int
    active_users: int
    pending_invitations: int
    user_activity_rate: float


class AcceptInvitationRequest(BaseModel):
    invitation_token: str
    password: str = Field(..., min_length=8)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    
    @validator("password")
    def validate_password(cls, v):
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class OrganizationUserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    first_name: str
    last_name: str
    full_name: str
    role_name: Optional[str]
    role_display_name: Optional[str]
    is_active: bool
    email_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class UpdateUserRoleRequest(BaseModel):
    role_id: str