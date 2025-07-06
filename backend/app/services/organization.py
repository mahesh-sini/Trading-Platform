"""
Organization Management Service for Multi-Tenancy
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import secrets
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.models.organization import (
    Organization, 
    OrganizationSettings, 
    UserInvitation,
    Role
)
from app.models.user import User
from app.services.rbac import RBACService
from app.core.config import settings
from app.core.security import get_password_hash, create_access_token


class OrganizationService:
    """Service for managing organizations and multi-tenancy"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rbac_service = RBACService(db)
    
    # Organization CRUD
    async def create_organization(
        self,
        name: str,
        display_name: str,
        slug: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        subscription_tier: str = "free",
        settings: Optional[Dict] = None
    ) -> Organization:
        """Create a new organization"""
        # Ensure slug is unique
        slug = await self._ensure_unique_slug(slug)
        
        organization = Organization(
            name=name,
            display_name=display_name,
            slug=slug,
            description=description,
            subscription_tier=subscription_tier,
            created_by=created_by
        )
        
        self.db.add(organization)
        await self.db.flush()  # Get the ID without committing
        
        # Create default organization settings
        org_settings = OrganizationSettings(
            organization_id=organization.id,
            **(settings or {})
        )
        self.db.add(org_settings)
        
        # Initialize default roles and permissions
        if created_by:
            await self.rbac_service.initialize_default_permissions()
            await self.rbac_service.initialize_default_roles(
                str(organization.id), 
                created_by
            )
        
        await self.db.commit()
        await self.db.refresh(organization)
        
        return organization
    
    async def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        result = await self.db.execute(
            select(Organization)
            .options(selectinload(Organization.users))
            .where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()
    
    async def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug"""
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def update_organization(
        self, 
        org_id: str, 
        updates: Dict[str, Any],
        updated_by: str
    ) -> Optional[Organization]:
        """Update organization"""
        organization = await self.get_organization(org_id)
        if not organization:
            return None
        
        # Store old values for audit
        old_values = {
            "name": organization.name,
            "display_name": organization.display_name,
            "description": organization.description
        }
        
        # Update fields
        for field, value in updates.items():
            if hasattr(organization, field):
                setattr(organization, field, value)
        
        await self.db.commit()
        await self.db.refresh(organization)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=org_id,
            user_id=updated_by,
            event_type="organization_updated",
            event_category="admin",
            action="update_organization",
            resource_type="organization",
            resource_id=org_id,
            old_values=old_values,
            new_values=updates
        )
        
        return organization
    
    async def delete_organization(self, org_id: str, deleted_by: str) -> bool:
        """Soft delete organization"""
        organization = await self.get_organization(org_id)
        if not organization:
            return False
        
        organization.is_active = False
        await self.db.commit()
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=org_id,
            user_id=deleted_by,
            event_type="organization_deleted",
            event_category="admin",
            action="delete_organization",
            resource_type="organization",
            resource_id=org_id
        )
        
        return True
    
    # Organization settings
    async def get_organization_settings(self, org_id: str) -> Optional[OrganizationSettings]:
        """Get organization settings"""
        result = await self.db.execute(
            select(OrganizationSettings).where(
                OrganizationSettings.organization_id == org_id
            )
        )
        return result.scalar_one_or_none()
    
    async def update_organization_settings(
        self, 
        org_id: str, 
        settings: Dict[str, Any],
        updated_by: str
    ) -> Optional[OrganizationSettings]:
        """Update organization settings"""
        org_settings = await self.get_organization_settings(org_id)
        
        if not org_settings:
            # Create settings if they don't exist
            org_settings = OrganizationSettings(
                organization_id=org_id,
                **settings
            )
            self.db.add(org_settings)
        else:
            # Update existing settings
            for field, value in settings.items():
                if hasattr(org_settings, field):
                    setattr(org_settings, field, value)
        
        await self.db.commit()
        await self.db.refresh(org_settings)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=org_id,
            user_id=updated_by,
            event_type="organization_settings_updated",
            event_category="admin",
            action="update_settings",
            resource_type="organization",
            resource_id=org_id,
            details=settings
        )
        
        return org_settings
    
    # User invitation and onboarding
    async def invite_user(
        self,
        organization_id: str,
        email: str,
        role_id: str,
        invited_by: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        message: Optional[str] = None,
        expires_in_days: int = 7
    ) -> UserInvitation:
        """Invite a user to join the organization"""
        # Generate invitation token
        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        invitation = UserInvitation(
            organization_id=organization_id,
            role_id=role_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            invitation_token=invitation_token,
            invited_by=invited_by,
            message=message,
            expires_at=expires_at
        )
        
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        
        # Send invitation email (mock implementation)
        await self._send_invitation_email(invitation)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=organization_id,
            user_id=invited_by,
            event_type="user_invited",
            event_category="admin",
            action="invite_user",
            resource_type="user",
            details={
                "email": email,
                "role_id": role_id,
                "invitation_id": str(invitation.id)
            }
        )
        
        return invitation
    
    async def accept_invitation(
        self,
        invitation_token: str,
        password: str,
        username: Optional[str] = None
    ) -> Optional[User]:
        """Accept a user invitation and create user account"""
        # Find valid invitation
        result = await self.db.execute(
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
            return None
        
        # Create user account
        user = User(
            organization_id=invitation.organization_id,
            role_id=invitation.role_id,
            email=invitation.email,
            username=username,
            first_name=invitation.first_name or "",
            last_name=invitation.last_name or "",
            password_hash=get_password_hash(password),
            account_status="active",
            email_verified=True  # Email is verified through invitation
        )
        
        self.db.add(user)
        
        # Update invitation status
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=invitation.organization_id,
            user_id=str(user.id),
            event_type="user_joined",
            event_category="security",
            action="accept_invitation",
            resource_type="user",
            resource_id=str(user.id),
            details={
                "email": invitation.email,
                "invitation_id": str(invitation.id)
            }
        )
        
        return user
    
    async def revoke_invitation(
        self, 
        invitation_id: str, 
        revoked_by: str
    ) -> Optional[UserInvitation]:
        """Revoke a pending invitation"""
        result = await self.db.execute(
            select(UserInvitation).where(UserInvitation.id == invitation_id)
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation or invitation.status != "pending":
            return None
        
        invitation.status = "revoked"
        await self.db.commit()
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=invitation.organization_id,
            user_id=revoked_by,
            event_type="invitation_revoked",
            event_category="admin",
            action="revoke_invitation",
            resource_type="user",
            details={
                "email": invitation.email,
                "invitation_id": str(invitation.id)
            }
        )
        
        return invitation
    
    async def get_organization_invitations(
        self, 
        organization_id: str,
        status: Optional[str] = None
    ) -> List[UserInvitation]:
        """Get all invitations for an organization"""
        query = select(UserInvitation).where(
            UserInvitation.organization_id == organization_id
        )
        
        if status:
            query = query.where(UserInvitation.status == status)
        
        query = query.order_by(UserInvitation.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # User management within organization
    async def add_user_to_organization(
        self,
        organization_id: str,
        user_id: str,
        role_id: str,
        added_by: str
    ) -> Optional[User]:
        """Add existing user to organization"""
        user = await self.db.get(User, user_id)
        if not user:
            return None
        
        user.organization_id = organization_id
        user.role_id = role_id
        
        await self.db.commit()
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=organization_id,
            user_id=added_by,
            event_type="user_added",
            event_category="admin",
            action="add_user",
            resource_type="user",
            resource_id=user_id,
            details={"role_id": role_id}
        )
        
        return user
    
    async def remove_user_from_organization(
        self,
        organization_id: str,
        user_id: str,
        removed_by: str
    ) -> bool:
        """Remove user from organization"""
        user = await self.db.get(User, user_id)
        if not user or user.organization_id != organization_id:
            return False
        
        user.is_active = False
        await self.db.commit()
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=organization_id,
            user_id=removed_by,
            event_type="user_removed",
            event_category="admin",
            action="remove_user",
            resource_type="user",
            resource_id=user_id
        )
        
        return True
    
    async def update_user_role(
        self,
        organization_id: str,
        user_id: str,
        new_role_id: str,
        updated_by: str
    ) -> Optional[User]:
        """Update user's role within organization"""
        user = await self.db.get(User, user_id)
        if not user or user.organization_id != organization_id:
            return None
        
        old_role_id = user.role_id
        user.role_id = new_role_id
        
        await self.db.commit()
        
        # Log audit event
        await self.rbac_service.log_audit_event(
            organization_id=organization_id,
            user_id=updated_by,
            event_type="user_role_updated",
            event_category="admin",
            action="update_user_role",
            resource_type="user",
            resource_id=user_id,
            old_values={"role_id": str(old_role_id)},
            new_values={"role_id": new_role_id}
        )
        
        return user
    
    # Organization analytics
    async def get_organization_stats(self, organization_id: str) -> Dict[str, Any]:
        """Get organization statistics"""
        # User count
        user_count_result = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.organization_id == organization_id,
                    User.is_active == True
                )
            )
        )
        user_count = user_count_result.scalar()
        
        # Active user count (logged in last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_user_count_result = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.organization_id == organization_id,
                    User.is_active == True,
                    User.last_login >= thirty_days_ago
                )
            )
        )
        active_user_count = active_user_count_result.scalar()
        
        # Invitation count
        pending_invitations_result = await self.db.execute(
            select(func.count(UserInvitation.id)).where(
                and_(
                    UserInvitation.organization_id == organization_id,
                    UserInvitation.status == "pending"
                )
            )
        )
        pending_invitations = pending_invitations_result.scalar()
        
        return {
            "total_users": user_count,
            "active_users": active_user_count,
            "pending_invitations": pending_invitations,
            "user_activity_rate": (active_user_count / user_count * 100) if user_count > 0 else 0
        }
    
    # Utility methods
    async def _ensure_unique_slug(self, slug: str) -> str:
        """Ensure organization slug is unique"""
        base_slug = slug
        counter = 1
        
        while True:
            result = await self.db.execute(
                select(Organization).where(Organization.slug == slug)
            )
            if not result.scalar_one_or_none():
                return slug
            
            slug = f"{base_slug}-{counter}"
            counter += 1
    
    async def _send_invitation_email(self, invitation: UserInvitation):
        """Send invitation email (mock implementation)"""
        # In a real implementation, this would use an email service
        print(f"Sending invitation email to {invitation.email}")
        print(f"Invitation token: {invitation.invitation_token}")
        print(f"Organization: {invitation.organization.name}")
        print(f"Role: {invitation.role.display_name}")
        
        # TODO: Implement actual email sending with template
        pass