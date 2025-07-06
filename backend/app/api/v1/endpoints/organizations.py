"""
Organization management API endpoints
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.organization import Organization, OrganizationSettings, UserInvitation
from app.services.organization import OrganizationService
from app.services.rbac import RBACService, require_permission
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationSettingsUpdate,
    UserInvitationCreate,
    UserInvitationResponse,
    OrganizationStatsResponse
)

router = APIRouter()


# Organization CRUD
@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization"""
    # Only system admins can create organizations
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create organizations"
        )
    
    org_service = OrganizationService(db)
    
    organization = await org_service.create_organization(
        name=org_data.name,
        display_name=org_data.display_name,
        slug=org_data.slug,
        description=org_data.description,
        created_by=str(current_user.id),
        subscription_tier=org_data.subscription_tier,
        settings=org_data.settings
    )
    
    return OrganizationResponse.from_orm(organization)


@router.get("/", response_model=List[OrganizationResponse])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    """List all organizations (admin only)"""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can list all organizations"
        )
    
    # TODO: Implement pagination and filtering
    # For now, return user's organization only
    return [OrganizationResponse.from_orm(current_user.organization)]


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's organization"""
    if not current_user.organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return OrganizationResponse.from_orm(current_user.organization)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization by ID"""
    org_service = OrganizationService(db)
    organization = await org_service.get_organization(org_id)
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user can access this organization
    if (str(current_user.organization_id) != org_id and 
        not current_user.is_admin()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return OrganizationResponse.from_orm(organization)


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    updates: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "org.settings", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org_service = OrganizationService(db)
    organization = await org_service.update_organization(
        org_id, 
        updates.dict(exclude_unset=True),
        str(current_user.id)
    )
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return OrganizationResponse.from_orm(organization)


@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete organization"""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete organizations"
        )
    
    org_service = OrganizationService(db)
    success = await org_service.delete_organization(org_id, str(current_user.id))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return {"message": "Organization deleted successfully"}


# Organization settings
@router.get("/{org_id}/settings", response_model=Dict[str, Any])
async def get_organization_settings(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization settings"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "org.settings", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org_service = OrganizationService(db)
    settings = await org_service.get_organization_settings(org_id)
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization settings not found"
        )
    
    return settings.__dict__


@router.put("/{org_id}/settings", response_model=Dict[str, Any])
async def update_organization_settings(
    org_id: str,
    settings_update: OrganizationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization settings"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "org.settings", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org_service = OrganizationService(db)
    settings = await org_service.update_organization_settings(
        org_id,
        settings_update.dict(exclude_unset=True),
        str(current_user.id)
    )
    
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return settings.__dict__


# User invitations
@router.post("/{org_id}/invitations", response_model=UserInvitationResponse)
async def invite_user(
    org_id: str,
    invitation_data: UserInvitationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite a user to join the organization"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.create", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to invite users"
        )
    
    org_service = OrganizationService(db)
    invitation = await org_service.invite_user(
        organization_id=org_id,
        email=invitation_data.email,
        role_id=invitation_data.role_id,
        invited_by=str(current_user.id),
        first_name=invitation_data.first_name,
        last_name=invitation_data.last_name,
        message=invitation_data.message
    )
    
    return UserInvitationResponse.from_orm(invitation)


@router.get("/{org_id}/invitations", response_model=List[UserInvitationResponse])
async def list_invitations(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status")
):
    """List organization invitations"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.read", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org_service = OrganizationService(db)
    invitations = await org_service.get_organization_invitations(
        org_id, status_filter
    )
    
    return [UserInvitationResponse.from_orm(inv) for inv in invitations]


@router.post("/invitations/{invitation_id}/revoke")
async def revoke_invitation(
    invitation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revoke a pending invitation"""
    # Check permission (simplified - should check org membership)
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.delete", str(current_user.organization_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org_service = OrganizationService(db)
    invitation = await org_service.revoke_invitation(
        invitation_id, str(current_user.id)
    )
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found or already processed"
        )
    
    return {"message": "Invitation revoked successfully"}


# Organization analytics
@router.get("/{org_id}/stats", response_model=OrganizationStatsResponse)
async def get_organization_stats(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization statistics"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "analytics.view_basic", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org_service = OrganizationService(db)
    stats = await org_service.get_organization_stats(org_id)
    
    return OrganizationStatsResponse(**stats)


# User management
@router.get("/{org_id}/users", response_model=List[Dict[str, Any]])
async def list_organization_users(
    org_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    include_inactive: bool = Query(False)
):
    """List all users in the organization"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.read", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    users = await rbac_service.get_organization_users(org_id, include_inactive)
    
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.display_name if user.role else None,
            "is_active": user.is_active,
            "last_login": user.last_login,
            "created_at": user.created_at
        }
        for user in users
    ]


@router.put("/{org_id}/users/{user_id}/role")
async def update_user_role(
    org_id: str,
    user_id: str,
    role_update: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's role in the organization"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.update", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org_service = OrganizationService(db)
    user = await org_service.update_user_role(
        org_id, user_id, role_update["role_id"], str(current_user.id)
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in organization"
        )
    
    return {"message": "User role updated successfully"}


@router.delete("/{org_id}/users/{user_id}")
async def remove_user_from_organization(
    org_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove user from organization"""
    # Check permission
    rbac_service = RBACService(db)
    if not await rbac_service.check_permission(
        str(current_user.id), "users.delete", org_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Prevent self-removal
    if user_id == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the organization"
        )
    
    org_service = OrganizationService(db)
    success = await org_service.remove_user_from_organization(
        org_id, user_id, str(current_user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in organization"
        )
    
    return {"message": "User removed from organization successfully"}