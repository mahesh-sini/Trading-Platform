from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from services.database import get_db
from services.auth_service import (
    hash_password, verify_password, create_token_response,
    verify_refresh_token, generate_verification_token,
    generate_reset_token, validate_password_strength
)
from models.user import User, UserRole, AccountStatus
from utils.email_service import send_verification_email, send_password_reset_email
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError('Password must be at least 8 characters with uppercase, lowercase, digit, and special character')
        return v
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if len(v.strip()) < 1:
            raise ValueError('Name cannot be empty')
        return v.strip()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError('Password must be at least 8 characters with uppercase, lowercase, digit, and special character')
        return v

class EmailVerification(BaseModel):
    token: str

# Authentication endpoints
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account"""
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Generate verification token
        verification_token = generate_verification_token()
        
        # Create new user
        new_user = User(
            email=user_data.email,
            password_hash=password_hash,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=UserRole.BASIC,
            account_status=AccountStatus.PENDING_VERIFICATION,
            email_verification_token=verification_token
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Send verification email in background
        background_tasks.add_task(
            send_verification_email,
            user_data.email,
            user_data.first_name,
            verification_token
        )
        
        # Create token response
        token_response = create_token_response(
            user_id=str(new_user.id),
            email=new_user.email,
            role=new_user.role.value
        )
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return {
            "message": "User registered successfully. Please check your email for verification.",
            "user": {
                "id": str(new_user.id),
                "email": new_user.email,
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "role": new_user.role.value,
                "account_status": new_user.account_status.value
            },
            **token_response
        }
        
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login")
async def login_user(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return tokens"""
    try:
        # Find user by email
        result = await db.execute(select(User).where(User.email == user_credentials.email))
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(user_credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check account status
        if user.account_status == AccountStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended"
            )
        
        if user.account_status == AccountStatus.INACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )
        
        # Update last login
        from datetime import datetime
        user.last_login = datetime.utcnow()
        await db.commit()
        
        # Create token response
        token_response = create_token_response(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value
        )
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return {
            "message": "Login successful",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.value,
                "account_status": user.account_status.value,
                "email_verified": user.email_verified
            },
            **token_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh")
async def refresh_access_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = verify_refresh_token(refresh_request.refresh_token)
        user_id = payload.get("sub")
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Create new token response
        token_response = create_token_response(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value
        )
        
        logger.info(f"Token refreshed for user: {user.email}")
        
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db)
):
    """Verify user email address"""
    try:
        # Find user by verification token
        result = await db.execute(
            select(User).where(User.email_verification_token == verification_data.token)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        # Update user status
        user.email_verified = True
        user.account_status = AccountStatus.ACTIVE
        user.email_verification_token = None
        
        await db.commit()
        
        logger.info(f"Email verified for user: {user.email}")
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

@router.post("/request-password-reset")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset"""
    try:
        # Find user by email
        result = await db.execute(select(User).where(User.email == reset_request.email))
        user = result.scalar_one_or_none()
        
        if user:
            # Generate reset token
            reset_token = generate_reset_token()
            from datetime import datetime, timedelta
            
            user.password_reset_token = reset_token
            user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
            
            await db.commit()
            
            # Send reset email in background
            background_tasks.add_task(
                send_password_reset_email,
                user.email,
                user.first_name,
                reset_token
            )
        
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using reset token"""
    try:
        # Find user by reset token
        result = await db.execute(
            select(User).where(User.password_reset_token == reset_data.token)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Check token expiration
        from datetime import datetime
        if user.password_reset_expires < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Update password
        user.password_hash = hash_password(reset_data.new_password)
        user.password_reset_token = None
        user.password_reset_expires = None
        
        await db.commit()
        
        logger.info(f"Password reset successfully for user: {user.email}")
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout user (client-side token removal)"""
    # In a stateless JWT system, logout is handled client-side
    # In production, you might want to implement token blacklisting
    logger.info("User logged out")
    return {"message": "Logged out successfully"}