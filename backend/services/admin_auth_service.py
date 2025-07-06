"""
Admin Authentication and RBAC Service
Handles admin login, session management, and role-based access control
"""

import jwt
import bcrypt
import pyotp
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import ipaddress
from dataclasses import dataclass
import logging

from ..models.admin import (
    Admin, AdminSession, AdminAuditLog, AdminPermission, 
    AdminRolePermission, AdminRoleEnum, AdminNotification
)
from ..services.database import get_db
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AuthResult:
    """Authentication result container"""
    success: bool
    admin: Optional[Admin] = None
    session: Optional[AdminSession] = None
    message: str = ""
    requires_mfa: bool = False
    error_code: Optional[str] = None


@dataclass
class PermissionCheck:
    """Permission check result"""
    allowed: bool
    reason: str = ""
    requires_approval: bool = False
    approval_level: str = ""


class AdminAuthService:
    """Comprehensive admin authentication and authorization service"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.token_expiry = timedelta(hours=8)
        self.max_login_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_mfa_secret(self) -> str:
        """Generate MFA secret for TOTP"""
        return pyotp.random_base32()
    
    def verify_mfa_token(self, secret: str, token: str) -> bool:
        """Verify MFA TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)
    
    def generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)
    
    def create_jwt_token(self, admin: Admin, session_id: str) -> str:
        """Create JWT token for admin session"""
        payload = {
            'admin_id': str(admin.id),
            'session_id': session_id,
            'role': admin.role.value,
            'exp': datetime.utcnow() + self.token_expiry,
            'iat': datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
    
    def is_ip_allowed(self, admin: Admin, ip_address: str) -> bool:
        """Check if IP address is allowed for admin"""
        if not admin.allowed_ip_addresses:
            return True  # No restrictions
        
        allowed_ips = admin.allowed_ip_addresses
        for allowed_ip in allowed_ips:
            try:
                if ipaddress.ip_address(ip_address) in ipaddress.ip_network(allowed_ip, strict=False):
                    return True
            except (ValueError, ipaddress.AddressValueError):
                # If it's not a valid IP/network, check for exact match
                if ip_address == allowed_ip:
                    return True
        
        return False
    
    def check_concurrent_sessions(self, db: Session, admin: Admin) -> bool:
        """Check if admin has exceeded concurrent session limit"""
        active_sessions = db.query(AdminSession).filter(
            and_(
                AdminSession.admin_id == admin.id,
                AdminSession.is_active == True,
                AdminSession.expires_at > datetime.utcnow()
            )
        ).count()
        
        return active_sessions < admin.max_concurrent_sessions
    
    def authenticate(
        self, 
        db: Session, 
        username: str, 
        password: str, 
        mfa_token: Optional[str] = None,
        ip_address: str = "unknown",
        user_agent: str = "unknown"
    ) -> AuthResult:
        """Authenticate admin user with comprehensive security checks"""
        
        # Find admin by username or email
        admin = db.query(Admin).filter(
            or_(
                Admin.username == username,
                Admin.email == username
            ),
            Admin.is_active == True
        ).first()
        
        if not admin:
            self._log_auth_attempt(db, None, "INVALID_USERNAME", ip_address, user_agent)
            return AuthResult(
                success=False, 
                message="Invalid credentials",
                error_code="INVALID_CREDENTIALS"
            )
        
        # Check if account is locked
        if admin.is_locked:
            if admin.locked_until and datetime.utcnow() < admin.locked_until:
                self._log_auth_attempt(db, admin, "ACCOUNT_LOCKED", ip_address, user_agent)
                return AuthResult(
                    success=False,
                    message="Account is locked",
                    error_code="ACCOUNT_LOCKED"
                )
            else:
                # Unlock account if lockout period has passed
                admin.is_locked = False
                admin.locked_until = None
                admin.login_attempts = 0
                db.commit()
        
        # Verify password
        if not self.verify_password(password, admin.password_hash):
            admin.login_attempts += 1
            
            # Lock account if too many failed attempts
            if admin.login_attempts >= self.max_login_attempts:
                admin.is_locked = True
                admin.locked_until = datetime.utcnow() + self.lockout_duration
                
                # Create security notification
                self._create_security_notification(
                    db, admin, "Account locked due to multiple failed login attempts"
                )
            
            db.commit()
            self._log_auth_attempt(db, admin, "INVALID_PASSWORD", ip_address, user_agent)
            return AuthResult(
                success=False,
                message="Invalid credentials",
                error_code="INVALID_CREDENTIALS"
            )
        
        # Check IP whitelist
        if not self.is_ip_allowed(admin, ip_address):
            self._log_auth_attempt(db, admin, "IP_NOT_ALLOWED", ip_address, user_agent)
            return AuthResult(
                success=False,
                message="IP address not allowed",
                error_code="IP_RESTRICTED"
            )
        
        # Check MFA if enabled
        if admin.is_mfa_enabled:
            if not mfa_token:
                return AuthResult(
                    success=False,
                    admin=admin,
                    message="MFA token required",
                    requires_mfa=True,
                    error_code="MFA_REQUIRED"
                )
            
            if not self.verify_mfa_token(admin.mfa_secret, mfa_token):
                admin.login_attempts += 1
                db.commit()
                self._log_auth_attempt(db, admin, "INVALID_MFA", ip_address, user_agent)
                return AuthResult(
                    success=False,
                    message="Invalid MFA token",
                    error_code="INVALID_MFA"
                )
        
        # Check concurrent sessions
        if not self.check_concurrent_sessions(db, admin):
            self._log_auth_attempt(db, admin, "MAX_SESSIONS_EXCEEDED", ip_address, user_agent)
            return AuthResult(
                success=False,
                message="Maximum concurrent sessions exceeded",
                error_code="MAX_SESSIONS"
            )
        
        # Create session
        session = self._create_session(db, admin, ip_address, user_agent)
        
        # Reset login attempts on successful login
        admin.login_attempts = 0
        admin.last_login = datetime.utcnow()
        db.commit()
        
        self._log_auth_attempt(db, admin, "LOGIN_SUCCESS", ip_address, user_agent, session.id)
        
        return AuthResult(
            success=True,
            admin=admin,
            session=session,
            message="Authentication successful"
        )
    
    def _create_session(
        self, 
        db: Session, 
        admin: Admin, 
        ip_address: str, 
        user_agent: str
    ) -> AdminSession:
        """Create new admin session"""
        session_token = self.generate_session_token()
        refresh_token = self.generate_session_token()
        
        session = AdminSession(
            admin_id=admin.id,
            session_token=session_token,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(minutes=admin.session_timeout_minutes),
            last_activity=datetime.utcnow(),
            browser_fingerprint=self._generate_fingerprint(user_agent, ip_address),
            risk_score=self._calculate_risk_score(admin, ip_address, user_agent)
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    def _generate_fingerprint(self, user_agent: str, ip_address: str) -> str:
        """Generate browser fingerprint"""
        data = f"{user_agent}:{ip_address}"
        return secrets.token_hex(16)
    
    def _calculate_risk_score(self, admin: Admin, ip_address: str, user_agent: str) -> float:
        """Calculate session risk score"""
        risk_score = 0.0
        
        # Add risk for new IP
        # Add risk for unusual user agent
        # Add risk for unusual login time
        # Add risk for role level
        
        if admin.role in [AdminRoleEnum.SUPER_ADMIN, AdminRoleEnum.SYSTEM_ADMIN]:
            risk_score += 30.0
        
        return min(risk_score, 100.0)
    
    def validate_session(self, db: Session, session_token: str) -> Optional[Admin]:
        """Validate admin session and return admin if valid"""
        session = db.query(AdminSession).filter(
            and_(
                AdminSession.session_token == session_token,
                AdminSession.is_active == True,
                AdminSession.is_revoked == False,
                AdminSession.expires_at > datetime.utcnow()
            )
        ).first()
        
        if not session:
            return None
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        db.commit()
        
        # Get admin
        admin = db.query(Admin).filter(
            and_(
                Admin.id == session.admin_id,
                Admin.is_active == True
            )
        ).first()
        
        return admin
    
    def logout(self, db: Session, session_token: str, admin_id: str = None) -> bool:
        """Logout admin by revoking session"""
        query = db.query(AdminSession).filter(
            AdminSession.session_token == session_token
        )
        
        if admin_id:
            query = query.filter(AdminSession.admin_id == admin_id)
        
        session = query.first()
        if session:
            session.is_active = False
            session.is_revoked = True
            session.revoked_reason = "user_logout"
            db.commit()
            
            self._log_auth_attempt(
                db, None, "LOGOUT", "unknown", "unknown", session.id
            )
            return True
        
        return False
    
    def revoke_session(
        self, 
        db: Session, 
        session_id: str, 
        revoked_by_admin_id: str, 
        reason: str = "admin_revoked"
    ) -> bool:
        """Revoke admin session (admin action)"""
        session = db.query(AdminSession).filter(
            AdminSession.id == session_id
        ).first()
        
        if session:
            session.is_active = False
            session.is_revoked = True
            session.revoked_by = revoked_by_admin_id
            session.revoked_reason = reason
            db.commit()
            
            # Log the revocation
            self._log_admin_action(
                db, revoked_by_admin_id, "SESSION_REVOKED",
                f"Revoked session {session_id}", session_id
            )
            return True
        
        return False
    
    def check_permission(
        self, 
        db: Session, 
        admin: Admin, 
        permission: str, 
        resource_id: str = None
    ) -> PermissionCheck:
        """Check if admin has specific permission"""
        
        # Super admin has all permissions
        if admin.role == AdminRoleEnum.SUPER_ADMIN:
            return PermissionCheck(allowed=True, reason="Super admin access")
        
        # Check role-based permissions
        role_permission = db.query(AdminRolePermission).join(
            AdminPermission
        ).filter(
            and_(
                AdminRolePermission.role == admin.role,
                AdminPermission.name == permission
            )
        ).first()
        
        if not role_permission:
            return PermissionCheck(
                allowed=False, 
                reason=f"Permission {permission} not granted to role {admin.role.value}"
            )
        
        # Check if permission requires approval
        if role_permission.permission.requires_approval:
            return PermissionCheck(
                allowed=True,
                requires_approval=True,
                approval_level=self._get_approval_level(admin.role, permission)
            )
        
        return PermissionCheck(allowed=True, reason="Permission granted")
    
    def _get_approval_level(self, role: AdminRoleEnum, permission: str) -> str:
        """Determine required approval level for permission"""
        # Define approval workflows based on role and permission
        approval_matrix = {
            "LARGE_REFUND": "FINANCIAL_MANAGER",
            "USER_SUSPENSION": "BUSINESS_ADMIN",
            "TRADING_HALT": "TRADING_MANAGER",
            "SYSTEM_CONFIG": "SYSTEM_ADMIN"
        }
        
        return approval_matrix.get(permission, "BUSINESS_ADMIN")
    
    def _log_auth_attempt(
        self, 
        db: Session, 
        admin: Optional[Admin], 
        action: str, 
        ip_address: str, 
        user_agent: str,
        session_id: str = None
    ):
        """Log authentication attempt"""
        log_entry = AdminAuditLog(
            admin_id=admin.id if admin else None,
            session_id=session_id,
            action=action,
            category="AUTHENTICATION",
            description=f"Authentication attempt: {action}",
            ip_address=ip_address,
            user_agent=user_agent,
            severity="INFO" if action == "LOGIN_SUCCESS" else "WARNING"
        )
        
        db.add(log_entry)
        db.commit()
    
    def _log_admin_action(
        self, 
        db: Session, 
        admin_id: str, 
        action: str, 
        description: str,
        resource_id: str = None
    ):
        """Log general admin action"""
        log_entry = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            category="ADMIN_ACTION",
            description=description,
            resource_id=resource_id,
            severity="INFO"
        )
        
        db.add(log_entry)
        db.commit()
    
    def _create_security_notification(
        self, 
        db: Session, 
        admin: Admin, 
        message: str
    ):
        """Create security notification for admin"""
        notification = AdminNotification(
            admin_id=admin.id,
            title="Security Alert",
            message=message,
            type="security",
            priority="high",
            category="security",
            requires_acknowledgment=True
        )
        
        db.add(notification)
        db.commit()


class RBACMiddleware:
    """Middleware for role-based access control"""
    
    def __init__(self, auth_service: AdminAuthService):
        self.auth_service = auth_service
    
    def require_permission(self, permission: str):
        """Decorator to require specific permission"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Extract admin from request context
                # This would be implemented based on your web framework
                pass
            return wrapper
        return decorator
    
    def require_role(self, min_role_level: int):
        """Decorator to require minimum role level"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Extract admin from request context
                # Check role level
                pass
            return wrapper
        return decorator