"""
Admin Security Middleware
Comprehensive security layer for admin panel operations
"""

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List, Callable, Any
from datetime import datetime, timedelta
import ipaddress
import asyncio
import json
import hashlib
from functools import wraps

from ..services.database import get_db
from ..services.admin_auth_service import AdminAuthService
from ..models.admin import Admin, AdminSession, AdminAuditLog, AdminRoleEnum
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Initialize security components
security = HTTPBearer()
auth_service = AdminAuthService(secret_key="your-secret-key")  # Should come from config


class SecurityConfig:
    """Security configuration settings"""
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_LOGIN_ATTEMPTS_PER_IP = 10
    
    # Session security
    SESSION_TIMEOUT_MINUTES = 480  # 8 hours
    MAX_CONCURRENT_SESSIONS = 3
    
    # IP restrictions
    ALLOWED_IP_RANGES = [
        "10.0.0.0/8",      # Private network
        "172.16.0.0/12",   # Private network
        "192.168.0.0/16",  # Private network
    ]
    
    # Dangerous actions requiring additional verification
    HIGH_RISK_ACTIONS = [
        "DELETE_USER",
        "BULK_USER_ACTION",
        "SYSTEM_CONFIG_CHANGE",
        "EMERGENCY_STOP",
        "LARGE_REFUND",
        "ADMIN_USER_CREATION"
    ]
    
    # Actions requiring MFA
    MFA_REQUIRED_ACTIONS = [
        "ADMIN_USER_CREATION",
        "ROLE_CHANGE",
        "SYSTEM_CONFIG_CHANGE",
        "EMERGENCY_STOP",
        "BULK_DELETE"
    ]


class SecurityMiddleware:
    """Comprehensive security middleware for admin operations"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.rate_limiter = RateLimiter()
        self.ip_validator = IPValidator(self.config.ALLOWED_IP_RANGES)
        self.session_manager = SessionManager()
    
    async def __call__(self, request: Request, call_next):
        """Main middleware entry point"""
        
        # Skip security for non-admin routes
        if not request.url.path.startswith("/admin"):
            return await call_next(request)
        
        # Skip for login endpoints
        if request.url.path in ["/admin/auth/login", "/admin/health"]:
            return await call_next(request)
        
        try:
            # 1. Rate limiting check
            await self.check_rate_limit(request)
            
            # 2. IP validation
            await self.validate_ip_address(request)
            
            # 3. Session validation
            admin = await self.validate_session(request)
            
            # 4. Permission check
            await self.check_permissions(request, admin)
            
            # 5. Risk assessment
            risk_score = await self.assess_risk(request, admin)
            
            # 6. Additional verification for high-risk actions
            if risk_score > 70:
                await self.require_additional_verification(request, admin)
            
            # Add admin to request state
            request.state.admin = admin
            request.state.risk_score = risk_score
            
            # Process request
            response = await call_next(request)
            
            # 7. Log the action
            await self.log_admin_action(request, admin, response.status_code)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal security error")
    
    async def check_rate_limit(self, request: Request):
        """Check rate limiting for the request"""
        client_ip = self.get_client_ip(request)
        
        if not await self.rate_limiter.is_allowed(client_ip, request.url.path):
            await self.log_security_event(
                "RATE_LIMIT_EXCEEDED",
                client_ip,
                {"path": request.url.path}
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
    
    async def validate_ip_address(self, request: Request):
        """Validate client IP address against allowed ranges"""
        client_ip = self.get_client_ip(request)
        
        if not self.ip_validator.is_allowed(client_ip):
            await self.log_security_event(
                "IP_ADDRESS_BLOCKED",
                client_ip,
                {"user_agent": request.headers.get("user-agent")}
            )
            raise HTTPException(
                status_code=403,
                detail="Access denied: IP address not authorized"
            )
    
    async def validate_session(self, request: Request) -> Admin:
        """Validate admin session and return admin user"""
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authentication required")
        
        token = auth_header.split(" ")[1]
        
        # Decode JWT token
        payload = auth_service.verify_jwt_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Validate session in database
        db = next(get_db())
        try:
            session = db.query(AdminSession).filter(
                AdminSession.id == payload["session_id"],
                AdminSession.is_active == True,
                AdminSession.expires_at > datetime.utcnow()
            ).first()
            
            if not session:
                raise HTTPException(status_code=401, detail="Session expired")
            
            # Get admin user
            admin = db.query(Admin).filter(
                Admin.id == session.admin_id,
                Admin.is_active == True
            ).first()
            
            if not admin:
                raise HTTPException(status_code=401, detail="Admin account not found")
            
            # Update session activity
            session.last_activity = datetime.utcnow()
            db.commit()
            
            return admin
            
        finally:
            db.close()
    
    async def check_permissions(self, request: Request, admin: Admin):
        """Check if admin has required permissions for the action"""
        
        # Super admin has all permissions
        if admin.role == AdminRoleEnum.SUPER_ADMIN:
            return
        
        # Extract action from request path and method
        action = self.extract_action(request)
        
        # Check role-based permissions
        db = next(get_db())
        try:
            permission_check = auth_service.check_permission(db, admin, action)
            if not permission_check.allowed:
                await self.log_security_event(
                    "PERMISSION_DENIED",
                    self.get_client_ip(request),
                    {
                        "admin_id": str(admin.id),
                        "action": action,
                        "reason": permission_check.reason
                    }
                )
                raise HTTPException(status_code=403, detail=permission_check.reason)
        finally:
            db.close()
    
    async def assess_risk(self, request: Request, admin: Admin) -> float:
        """Assess risk score for the current request"""
        risk_score = 0.0
        
        # Base risk by role
        role_risk = {
            AdminRoleEnum.SUPER_ADMIN: 40.0,
            AdminRoleEnum.SYSTEM_ADMIN: 30.0,
            AdminRoleEnum.BUSINESS_ADMIN: 20.0,
            AdminRoleEnum.TRADING_MANAGER: 25.0,
            AdminRoleEnum.FINANCIAL_MANAGER: 25.0,
            AdminRoleEnum.SUPPORT_MANAGER: 15.0,
            AdminRoleEnum.SUPPORT_AGENT: 5.0,
            AdminRoleEnum.CONTENT_MANAGER: 5.0,
            AdminRoleEnum.DATA_ANALYST: 5.0,
            AdminRoleEnum.SECURITY_ANALYST: 15.0
        }
        
        risk_score += role_risk.get(admin.role, 0.0)
        
        # Risk by action type
        action = self.extract_action(request)
        if action in self.config.HIGH_RISK_ACTIONS:
            risk_score += 30.0
        
        # Risk by request method
        if request.method in ["DELETE", "PUT"]:
            risk_score += 10.0
        elif request.method == "POST":
            risk_score += 5.0
        
        # Risk by time of day (higher risk outside business hours)
        current_hour = datetime.utcnow().hour
        if current_hour < 6 or current_hour > 22:  # Outside 6 AM - 10 PM UTC
            risk_score += 15.0
        
        # Risk by IP address (new or unusual IPs)
        client_ip = self.get_client_ip(request)
        if await self.is_new_ip_for_admin(admin, client_ip):
            risk_score += 20.0
        
        return min(risk_score, 100.0)
    
    async def require_additional_verification(self, request: Request, admin: Admin):
        """Require additional verification for high-risk actions"""
        
        # Check if MFA verification is in headers
        mfa_token = request.headers.get("x-mfa-token")
        if not mfa_token:
            raise HTTPException(
                status_code=423,
                detail={
                    "error": "additional_verification_required",
                    "message": "This action requires MFA verification",
                    "verification_type": "mfa"
                }
            )
        
        # Verify MFA token
        if not auth_service.verify_mfa_token(admin.mfa_secret, mfa_token):
            await self.log_security_event(
                "MFA_VERIFICATION_FAILED",
                self.get_client_ip(request),
                {"admin_id": str(admin.id)}
            )
            raise HTTPException(status_code=401, detail="Invalid MFA token")
    
    def extract_action(self, request: Request) -> str:
        """Extract action type from request path and method"""
        path_parts = request.url.path.split("/")
        method = request.method
        
        # Map paths to actions
        action_mapping = {
            ("admin", "users", "POST"): "CREATE_USER",
            ("admin", "users", "PUT"): "MODIFY_USER",
            ("admin", "users", "DELETE"): "DELETE_USER",
            ("admin", "subscriptions", "POST"): "CREATE_SUBSCRIPTION",
            ("admin", "trading", "POST"): "TRADING_ACTION",
            ("admin", "system", "PUT"): "SYSTEM_CONFIG_CHANGE",
        }
        
        # Try to find exact match
        key = tuple(path_parts[1:4] + [method] if len(path_parts) >= 4 else path_parts[1:] + [method])
        return action_mapping.get(key, f"{method}_{path_parts[-1].upper()}")
    
    def get_client_ip(self, request: Request) -> str:
        """Get real client IP address"""
        # Check for forwarded IP headers
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def is_new_ip_for_admin(self, admin: Admin, ip_address: str) -> bool:
        """Check if this is a new IP address for the admin"""
        db = next(get_db())
        try:
            recent_session = db.query(AdminSession).filter(
                AdminSession.admin_id == admin.id,
                AdminSession.ip_address == ip_address,
                AdminSession.created_at > datetime.utcnow() - timedelta(days=30)
            ).first()
            
            return recent_session is None
        finally:
            db.close()
    
    async def log_admin_action(self, request: Request, admin: Admin, status_code: int):
        """Log admin action for audit trail"""
        db = next(get_db())
        try:
            log_entry = AdminAuditLog(
                admin_id=admin.id,
                action=self.extract_action(request),
                category="WEB_REQUEST",
                description=f"{request.method} {request.url.path}",
                ip_address=self.get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                request_path=str(request.url.path),
                request_method=request.method,
                severity="INFO" if status_code < 400 else "WARNING"
            )
            
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log admin action: {str(e)}")
        finally:
            db.close()
    
    async def log_security_event(self, event_type: str, ip_address: str, details: dict):
        """Log security event"""
        db = next(get_db())
        try:
            log_entry = AdminAuditLog(
                action=event_type,
                category="SECURITY",
                description=f"Security event: {event_type}",
                ip_address=ip_address,
                severity="WARNING",
                after_state=details
            )
            
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")
        finally:
            db.close()


class RateLimiter:
    """Rate limiting implementation"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = datetime.utcnow()
    
    async def is_allowed(self, client_ip: str, path: str) -> bool:
        """Check if request is allowed based on rate limits"""
        now = datetime.utcnow()
        
        # Clean up old entries periodically
        if (now - self.last_cleanup).seconds > self.cleanup_interval:
            await self.cleanup_old_entries()
        
        # Create key for this client and path
        key = f"{client_ip}:{path}"
        
        # Get current request count
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove requests older than 1 minute
        minute_ago = now - timedelta(minutes=1)
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if timestamp > minute_ago
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= SecurityConfig.MAX_REQUESTS_PER_MINUTE:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True
    
    async def cleanup_old_entries(self):
        """Clean up old rate limiting entries"""
        cutoff = datetime.utcnow() - timedelta(hours=1)
        
        for key in list(self.requests.keys()):
            self.requests[key] = [
                timestamp for timestamp in self.requests[key]
                if timestamp > cutoff
            ]
            
            if not self.requests[key]:
                del self.requests[key]
        
        self.last_cleanup = datetime.utcnow()


class IPValidator:
    """IP address validation"""
    
    def __init__(self, allowed_ranges: List[str]):
        self.allowed_networks = []
        for range_str in allowed_ranges:
            try:
                self.allowed_networks.append(ipaddress.ip_network(range_str, strict=False))
            except ValueError:
                logger.warning(f"Invalid IP range in config: {range_str}")
    
    def is_allowed(self, ip_address: str) -> bool:
        """Check if IP address is in allowed ranges"""
        if not self.allowed_networks:
            return True  # No restrictions configured
        
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Always allow localhost
            if ip.is_loopback:
                return True
            
            # Check against allowed networks
            for network in self.allowed_networks:
                if ip in network:
                    return True
            
            return False
            
        except ValueError:
            logger.warning(f"Invalid IP address: {ip_address}")
            return False


class SessionManager:
    """Session management utilities"""
    
    def __init__(self):
        pass
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        db = next(get_db())
        try:
            expired_sessions = db.query(AdminSession).filter(
                AdminSession.expires_at < datetime.utcnow(),
                AdminSession.is_active == True
            ).all()
            
            for session in expired_sessions:
                session.is_active = False
                session.is_revoked = True
                session.revoked_reason = "expired"
            
            db.commit()
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        except Exception as e:
            logger.error(f"Failed to cleanup sessions: {str(e)}")
        finally:
            db.close()


# Decorator for additional permission checks
def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get admin from request state (set by middleware)
            request = kwargs.get('request')
            if request and hasattr(request.state, 'admin'):
                admin = request.state.admin
                
                # Check permission
                db = next(get_db())
                try:
                    permission_check = auth_service.check_permission(db, admin, permission)
                    if not permission_check.allowed:
                        raise HTTPException(status_code=403, detail=permission_check.reason)
                finally:
                    db.close()
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_mfa(func: Callable) -> Callable:
    """Decorator to require MFA for specific actions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if request:
            mfa_token = request.headers.get("x-mfa-token")
            if not mfa_token:
                raise HTTPException(
                    status_code=423,
                    detail={
                        "error": "mfa_required",
                        "message": "This action requires MFA verification"
                    }
                )
        
        return await func(*args, **kwargs)
    return wrapper