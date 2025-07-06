"""
Multi-tenant middleware for request isolation
"""

from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.database import SessionLocal
from models.user import User
from app.models.organization import Organization
from app.core.security import decode_access_token
import logging

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to handle multi-tenant request isolation"""
    
    def __init__(self, app, tenant_header: str = "X-Organization-ID"):
        super().__init__(app)
        self.tenant_header = tenant_header
        self.excluded_paths = {
            "/docs", "/redoc", "/openapi.json",
            "/health", "/metrics",
            "/api/v1/auth/login", "/api/v1/auth/register",
            "/api/v1/invitations/validate", "/api/v1/invitations/accept",
            "/api/v1/invitations/organization"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip tenant validation for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Skip for OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        try:
            # Extract tenant information
            await self._set_tenant_context(request)
            
            # Process request
            response = await call_next(request)
            
            return response
            
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            logger.error(f"Tenant middleware error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
    
    async def _set_tenant_context(self, request: Request):
        """Set tenant context for the request"""
        # Get authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # Some endpoints may not require authentication
            return
        
        # Extract token
        token = auth_header.split(" ")[1]
        
        try:
            # Decode token to get user ID
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
            # Get user and organization from database
            async with SessionLocal() as db:
                result = await db.execute(
                    select(User)
                    .join(Organization)
                    .where(User.id == user_id)
                    .where(User.is_active == True)
                    .where(Organization.is_active == True)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found or inactive"
                    )
                
                if not user.organization:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User not associated with any organization"
                    )
                
                # Set tenant context in request state
                request.state.user_id = str(user.id)
                request.state.organization_id = str(user.organization_id)
                request.state.tenant_slug = user.organization.slug
                
                # Optionally validate organization header if provided
                org_header = request.headers.get(self.tenant_header)
                if org_header and org_header != str(user.organization_id):
                    logger.warning(
                        f"Organization header mismatch: header={org_header}, "
                        f"user_org={user.organization_id}, user={user_id}"
                    )
                    # For security, we could reject the request here
                    # raise HTTPException(
                    #     status_code=status.HTTP_403_FORBIDDEN,
                    #     detail="Organization access denied"
                    # )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error setting tenant context: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )


class TenantIsolationMixin:
    """Mixin to add tenant isolation to database queries"""
    
    @staticmethod
    def filter_by_organization(query, model, organization_id: str):
        """Add organization filter to query"""
        if hasattr(model, 'organization_id'):
            return query.where(model.organization_id == organization_id)
        return query
    
    @staticmethod
    def ensure_organization_access(instance, organization_id: str):
        """Ensure the instance belongs to the organization"""
        if hasattr(instance, 'organization_id'):
            if str(instance.organization_id) != organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization's resources"
                )
        elif hasattr(instance, 'user') and hasattr(instance.user, 'organization_id'):
            if str(instance.user.organization_id) != organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization's resources"
                )


def get_tenant_context(request: Request) -> tuple[str, str]:
    """Get tenant context from request"""
    organization_id = getattr(request.state, 'organization_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    if not organization_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context not available"
        )
    
    return organization_id, user_id


class TenantAwareSession:
    """Session wrapper that automatically applies tenant filters"""
    
    def __init__(self, db: AsyncSession, organization_id: str):
        self.db = db
        self.organization_id = organization_id
    
    async def get_organization_data(self, model, **filters):
        """Get data filtered by organization"""
        query = select(model).where(model.organization_id == self.organization_id)
        
        for field, value in filters.items():
            if hasattr(model, field):
                query = query.where(getattr(model, field) == value)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_user_data(self, model, user_id: str, **filters):
        """Get user data within organization"""
        query = select(model).where(
            model.organization_id == self.organization_id,
            model.user_id == user_id
        )
        
        for field, value in filters.items():
            if hasattr(model, field):
                query = query.where(getattr(model, field) == value)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    def ensure_organization_isolation(self, instance):
        """Ensure instance belongs to current organization"""
        if hasattr(instance, 'organization_id'):
            if str(instance.organization_id) != self.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-tenant access denied"
                )
        
        return instance


# Dependency to get tenant-aware session
async def get_tenant_session(
    request: Request,
    db: AsyncSession
) -> TenantAwareSession:
    """Get tenant-aware database session"""
    organization_id, _ = get_tenant_context(request)
    return TenantAwareSession(db, organization_id)


# Utility functions for tenant-aware operations
def apply_tenant_filter(query, model, organization_id: str):
    """Apply tenant filter to SQLAlchemy query"""
    if hasattr(model, 'organization_id'):
        return query.where(model.organization_id == organization_id)
    return query


def validate_tenant_access(resource, organization_id: str):
    """Validate that resource belongs to organization"""
    if hasattr(resource, 'organization_id'):
        if str(resource.organization_id) != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: resource belongs to different organization"
            )
    elif hasattr(resource, 'user') and hasattr(resource.user, 'organization_id'):
        if str(resource.user.organization_id) != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: resource owner belongs to different organization"
            )


def ensure_same_organization(*resources):
    """Ensure all resources belong to the same organization"""
    org_ids = set()
    
    for resource in resources:
        if hasattr(resource, 'organization_id'):
            org_ids.add(str(resource.organization_id))
        elif hasattr(resource, 'user') and hasattr(resource.user, 'organization_id'):
            org_ids.add(str(resource.user.organization_id))
    
    if len(org_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resources belong to different organizations"
        )
    
    return list(org_ids)[0] if org_ids else None