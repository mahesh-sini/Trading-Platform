from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, Dict, Any
from services.database import get_db
from services.auth_service import hash_password, verify_password
from models.user import User, UserRole, AccountStatus
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class UserProfile(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    timezone: str = "UTC"
    preferences: Optional[Dict[str, Any]] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        from services.auth_service import validate_password_strength
        if not validate_password_strength(v):
            raise ValueError('Password must be at least 8 characters with uppercase, lowercase, digit, and special character')
        return v

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: str
    account_status: str
    email_verified: bool
    timezone: str
    preferences: Optional[Dict[str, Any]]
    created_at: str
    last_login: Optional[str]

@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: dict = Depends(lambda: {}),  # Will be replaced with actual auth dependency
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Parse preferences JSON if it exists
        preferences = None
        if user.preferences:
            try:
                preferences = json.loads(user.preferences)
            except json.JSONDecodeError:
                preferences = {}
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            role=user.role.value,
            account_status=user.account_status.value,
            email_verified=user.email_verified,
            timezone=user.timezone,
            preferences=preferences,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )

@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    profile_data: UserProfile,
    current_user: dict = Depends(lambda: {}),  # Will be replaced with actual auth dependency
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user fields
        user.first_name = profile_data.first_name
        user.last_name = profile_data.last_name
        user.phone = profile_data.phone
        user.timezone = profile_data.timezone
        
        if profile_data.preferences:
            user.preferences = json.dumps(profile_data.preferences)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User profile updated: {user.email}")
        
        # Parse preferences for response
        preferences = None
        if user.preferences:
            try:
                preferences = json.loads(user.preferences)
            except json.JSONDecodeError:
                preferences = {}
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            role=user.role.value,
            account_status=user.account_status.value,
            email_verified=user.email_verified,
            timezone=user.timezone,
            preferences=preferences,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user profile: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(lambda: {}),  # Will be replaced with actual auth dependency
    db: AsyncSession = Depends(get_db)
):
    """Change user's password"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.password_hash = hash_password(password_data.new_password)
        await db.commit()
        
        logger.info(f"Password changed for user: {user.email}")
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.delete("/account")
async def delete_user_account(
    current_user: dict = Depends(lambda: {}),  # Will be replaced with actual auth dependency
    db: AsyncSession = Depends(get_db)
):
    """Delete user account (soft delete)"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete by setting account status to inactive
        user.account_status = AccountStatus.INACTIVE
        user.is_active = False
        
        await db.commit()
        
        logger.info(f"User account deleted: {user.email}")
        
        return {"message": "Account deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user account: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )

@router.get("/preferences")
async def get_user_preferences(
    current_user: dict = Depends(lambda: {}),  # Will be replaced with actual auth dependency
    db: AsyncSession = Depends(get_db)
):
    """Get user preferences"""
    try:
        user_id = current_user.get("sub")
        
        result = await db.execute(select(User.preferences).where(User.id == user_id))
        preferences_json = result.scalar_one_or_none()
        
        if preferences_json:
            try:
                preferences = json.loads(preferences_json)
            except json.JSONDecodeError:
                preferences = {}
        else:
            preferences = {}
        
        return {"preferences": preferences}
        
    except Exception as e:
        logger.error(f"Failed to get user preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences"
        )

@router.put("/preferences")
async def update_user_preferences(
    preferences: Dict[str, Any],
    current_user: dict = Depends(lambda: {}),  # Will be replaced with actual auth dependency
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences"""
    try:
        user_id = current_user.get("sub")
        
        # Update preferences
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(preferences=json.dumps(preferences))
        )
        await db.commit()
        
        logger.info(f"User preferences updated for user: {user_id}")
        
        return {"message": "Preferences updated successfully", "preferences": preferences}
        
    except Exception as e:
        logger.error(f"Failed to update user preferences: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )