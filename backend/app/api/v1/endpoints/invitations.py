"""
Public invitation endpoints (no authentication required)
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.organization import OrganizationService
from app.schemas.organization import AcceptInvitationRequest
from app.schemas.auth import UserResponse
from app.core.security import create_access_token

router = APIRouter()


@router.get("/validate/{invitation_token}")
async def validate_invitation(
    invitation_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Validate an invitation token"""
    org_service = OrganizationService(db)
    
    # Get invitation details without accepting it
    from sqlalchemy import select, and_
    from app.models.organization import UserInvitation
    from sqlalchemy.orm import selectinload
    from datetime import datetime
    
    result = await db.execute(
        select(UserInvitation)
        .options(selectinload(UserInvitation.organization))
        .options(selectinload(UserInvitation.role))
        .where(
            and_(
                UserInvitation.invitation_token == invitation_token,
                UserInvitation.status == "pending",
                UserInvitation.expires_at > datetime.utcnow()
            )
        )
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation"
        )
    
    return {
        "valid": True,
        "organization": {
            "name": invitation.organization.display_name,
            "slug": invitation.organization.slug
        },
        "role": {
            "name": invitation.role.display_name,
            "description": invitation.role.description
        },
        "email": invitation.email,
        "first_name": invitation.first_name,
        "last_name": invitation.last_name,
        "expires_at": invitation.expires_at,
        "invited_by": invitation.inviter.full_name if invitation.inviter else None
    }


@router.post("/accept")
async def accept_invitation(
    invitation_data: AcceptInvitationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Accept an invitation and create user account"""
    org_service = OrganizationService(db)
    
    user = await org_service.accept_invitation(
        invitation_token=invitation_data.invitation_token,
        password=invitation_data.password,
        username=invitation_data.username
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation"
        )
    
    # Create access token for the new user
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "organization": {
                "id": str(user.organization_id),
                "name": user.organization.display_name,
                "slug": user.organization.slug
            },
            "role": {
                "id": str(user.role_id),
                "name": user.role.display_name
            }
        },
        "message": "Account created successfully"
    }


@router.get("/organization/{slug}")
async def get_organization_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get public organization information by slug"""
    org_service = OrganizationService(db)
    organization = await org_service.get_organization_by_slug(slug)
    
    if not organization or not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    return {
        "name": organization.display_name,
        "slug": organization.slug,
        "description": organization.description,
        "is_verified": organization.is_verified
    }