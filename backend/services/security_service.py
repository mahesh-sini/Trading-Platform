"""
Comprehensive Security Service
Implements security hardening, compliance, and protection measures
"""

import asyncio
import logging
import hashlib
import hmac
import secrets
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import ipaddress
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bcrypt
import jwt
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
import redis
import os

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security levels for different operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """Types of security threats"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    DDOS = "ddos"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH = "data_breach"
    MALFORMED_REQUEST = "malformed_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

@dataclass
class SecurityEvent:
    """Security event record"""
    event_id: str
    threat_type: ThreatType
    severity: SecurityLevel
    timestamp: datetime
    source_ip: str
    user_id: Optional[str]
    description: str
    metadata: Dict[str, Any]
    blocked: bool = False

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int
    window_size: int = 60  # seconds

class SecurityService:
    """Comprehensive security service"""
    
    def __init__(self):
        # Encryption
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Redis for security tracking
        self.redis_client = None
        
        # Security configurations
        self.rate_limits = {
            '/api/auth/login': RateLimitConfig(5, 30, 100, 10),
            '/api/auth/register': RateLimitConfig(3, 10, 20, 5),
            '/api/trading/order': RateLimitConfig(60, 500, 2000, 100),
            '/api/ml/predict': RateLimitConfig(100, 1000, 5000, 200),
            'default': RateLimitConfig(120, 1000, 10000, 240)
        }
        
        # Blocked IPs and patterns
        self.blocked_ips: set = set()
        self.suspicious_patterns = [
            r'(union|select|insert|delete|drop|create|alter)\s+',
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'onclick\s*=',
            r'onerror\s*=',
            r'onload\s*=',
        ]
        
        # Security events storage
        self.security_events: List[SecurityEvent] = []
        self.max_events = 10000
        
        # Failed login tracking
        self.failed_login_attempts: Dict[str, List[datetime]] = {}
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
        
        # API key management
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        
        # Monitoring task
        self._monitoring_task = None
    
    async def initialize(self):
        """Initialize security service"""
        try:
            # Initialize Redis connection
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            
            # Load blocked IPs
            await self._load_blocked_ips()
            
            # Start security monitoring
            self._monitoring_task = asyncio.create_task(self._security_monitor())
            
            logger.info("Security service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize security service: {e}")
            raise
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key"""
        key_file = Path("security/encryption.key")
        key_file.parent.mkdir(exist_ok=True)
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    async def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    async def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    async def check_request_security(self, request: Request) -> bool:
        """Comprehensive request security check"""
        try:
            client_ip = self._get_client_ip(request)
            endpoint = request.url.path
            
            # Check if IP is blocked
            if await self._is_ip_blocked(client_ip):
                await self._log_security_event(
                    ThreatType.UNAUTHORIZED_ACCESS,
                    SecurityLevel.HIGH,
                    client_ip,
                    f"Request from blocked IP: {endpoint}",
                    {"endpoint": endpoint, "method": request.method}
                )
                return False
            
            # Rate limiting check
            if not await self._check_rate_limit(client_ip, endpoint):
                await self._log_security_event(
                    ThreatType.RATE_LIMIT_EXCEEDED,
                    SecurityLevel.MEDIUM,
                    client_ip,
                    f"Rate limit exceeded: {endpoint}",
                    {"endpoint": endpoint, "method": request.method}
                )
                return False
            
            # Check for malicious patterns
            if await self._check_malicious_patterns(request):
                await self._log_security_event(
                    ThreatType.XSS,
                    SecurityLevel.HIGH,
                    client_ip,
                    f"Malicious pattern detected: {endpoint}",
                    {"endpoint": endpoint, "method": request.method}
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Security check failed: {e}")
            return False
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    async def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        if ip in self.blocked_ips:
            return True
        
        # Check Redis for temporary blocks
        if self.redis_client:
            blocked = await asyncio.to_thread(
                self.redis_client.get, f"blocked_ip:{ip}"
            )
            return blocked is not None
        
        return False
    
    async def _check_rate_limit(self, ip: str, endpoint: str) -> bool:
        """Check rate limiting for IP and endpoint"""
        try:
            # Get rate limit config
            config = self.rate_limits.get(endpoint, self.rate_limits['default'])
            
            current_time = datetime.now()
            
            if self.redis_client:
                # Use Redis for distributed rate limiting
                pipe = self.redis_client.pipeline()
                
                # Check minute limit
                minute_key = f"rate_limit:{ip}:{endpoint}:minute:{current_time.minute}"
                pipe.incr(minute_key)
                pipe.expire(minute_key, 60)
                
                # Check hour limit
                hour_key = f"rate_limit:{ip}:{endpoint}:hour:{current_time.hour}"
                pipe.incr(hour_key)
                pipe.expire(hour_key, 3600)
                
                # Check day limit
                day_key = f"rate_limit:{ip}:{endpoint}:day:{current_time.date()}"
                pipe.incr(day_key)
                pipe.expire(day_key, 86400)
                
                results = await asyncio.to_thread(pipe.execute)
                
                minute_count, _, hour_count, _, day_count, _ = results
                
                if (minute_count > config.requests_per_minute or
                    hour_count > config.requests_per_hour or
                    day_count > config.requests_per_day):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error to avoid blocking legitimate users
    
    async def _check_malicious_patterns(self, request: Request) -> bool:
        """Check for malicious patterns in request"""
        try:
            # Check URL path
            url_path = str(request.url.path)
            for pattern in self.suspicious_patterns:
                if re.search(pattern, url_path, re.IGNORECASE):
                    return True
            
            # Check query parameters
            query_params = str(request.url.query)
            for pattern in self.suspicious_patterns:
                if re.search(pattern, query_params, re.IGNORECASE):
                    return True
            
            # Check headers
            for header_name, header_value in request.headers.items():
                for pattern in self.suspicious_patterns:
                    if re.search(pattern, header_value, re.IGNORECASE):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Malicious pattern check failed: {e}")
            return False
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return associated metadata"""
        try:
            if not api_key:
                return None
            
            # Hash the API key for lookup
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            if self.redis_client:
                api_key_data = await asyncio.to_thread(
                    self.redis_client.get, f"api_key:{key_hash}"
                )
                if api_key_data:
                    return json.loads(api_key_data)
            
            # Fallback to in-memory storage
            return self.api_keys.get(key_hash)
            
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return None
    
    async def create_api_key(
        self, 
        user_id: str, 
        permissions: List[str],
        expires_in_days: int = 365
    ) -> Tuple[str, str]:
        """Create a new API key"""
        try:
            # Generate secure API key
            api_key = secrets.token_urlsafe(32)
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Create metadata
            metadata = {
                'user_id': user_id,
                'permissions': permissions,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=expires_in_days)).isoformat(),
                'is_active': True,
                'usage_count': 0
            }
            
            # Store in Redis
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"api_key:{key_hash}",
                    expires_in_days * 86400,
                    json.dumps(metadata)
                )
            
            # Store in memory as backup
            self.api_keys[key_hash] = metadata
            
            logger.info(f"API key created for user {user_id}")
            return api_key, key_hash
            
        except Exception as e:
            logger.error(f"API key creation failed: {e}")
            raise
    
    async def track_failed_login(self, identifier: str, ip: str) -> bool:
        """Track failed login attempts and return if account should be locked"""
        try:
            current_time = datetime.now()
            
            # Initialize if not exists
            if identifier not in self.failed_login_attempts:
                self.failed_login_attempts[identifier] = []
            
            # Add current attempt
            self.failed_login_attempts[identifier].append(current_time)
            
            # Clean old attempts (outside lockout window)
            cutoff_time = current_time - self.lockout_duration
            self.failed_login_attempts[identifier] = [
                attempt for attempt in self.failed_login_attempts[identifier]
                if attempt > cutoff_time
            ]
            
            # Check if threshold exceeded
            attempts_count = len(self.failed_login_attempts[identifier])
            
            if attempts_count >= self.max_failed_attempts:
                # Lock account
                await self._lock_account(identifier, ip)
                
                await self._log_security_event(
                    ThreatType.BRUTE_FORCE,
                    SecurityLevel.HIGH,
                    ip,
                    f"Account locked due to {attempts_count} failed login attempts",
                    {"identifier": identifier, "attempts": attempts_count}
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed login tracking error: {e}")
            return False
    
    async def _lock_account(self, identifier: str, ip: str):
        """Lock account temporarily"""
        try:
            if self.redis_client:
                # Lock account for lockout duration
                lockout_seconds = int(self.lockout_duration.total_seconds())
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"locked_account:{identifier}",
                    lockout_seconds,
                    json.dumps({
                        'locked_at': datetime.now().isoformat(),
                        'locked_by_ip': ip,
                        'reason': 'excessive_failed_logins'
                    })
                )
            
            logger.warning(f"Account {identifier} locked due to failed login attempts")
            
        except Exception as e:
            logger.error(f"Account locking failed: {e}")
    
    async def is_account_locked(self, identifier: str) -> bool:
        """Check if account is locked"""
        try:
            if self.redis_client:
                locked_data = await asyncio.to_thread(
                    self.redis_client.get, f"locked_account:{identifier}"
                )
                return locked_data is not None
            
            return False
            
        except Exception as e:
            logger.error(f"Account lock check failed: {e}")
            return False
    
    async def sanitize_input(self, input_data: str) -> str:
        """Sanitize user input to prevent injection attacks"""
        try:
            # Remove potentially dangerous characters
            sanitized = re.sub(r'[<>"\';()&+]', '', input_data)
            
            # Limit length
            sanitized = sanitized[:1000]
            
            # Remove SQL injection patterns
            sql_patterns = [
                r'\bunion\b', r'\bselect\b', r'\binsert\b', r'\bdelete\b',
                r'\bdrop\b', r'\bcreate\b', r'\balter\b', r'\bexec\b'
            ]
            
            for pattern in sql_patterns:
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
            
            return sanitized.strip()
            
        except Exception as e:
            logger.error(f"Input sanitization failed: {e}")
            return ""
    
    async def generate_csrf_token(self, user_id: str) -> str:
        """Generate CSRF token for user session"""
        try:
            timestamp = str(int(datetime.now().timestamp()))
            message = f"{user_id}:{timestamp}"
            
            # Create HMAC signature
            secret_key = os.getenv('CSRF_SECRET', 'default-csrf-secret')
            signature = hmac.new(
                secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            token = f"{timestamp}.{signature}"
            
            # Store token in Redis
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"csrf_token:{user_id}",
                    3600,  # 1 hour expiry
                    token
                )
            
            return token
            
        except Exception as e:
            logger.error(f"CSRF token generation failed: {e}")
            raise
    
    async def validate_csrf_token(self, user_id: str, token: str) -> bool:
        """Validate CSRF token"""
        try:
            if not token or '.' not in token:
                return False
            
            timestamp_str, signature = token.split('.', 1)
            
            # Check token age (max 1 hour)
            token_time = datetime.fromtimestamp(int(timestamp_str))
            if datetime.now() - token_time > timedelta(hours=1):
                return False
            
            # Verify signature
            message = f"{user_id}:{timestamp_str}"
            secret_key = os.getenv('CSRF_SECRET', 'default-csrf-secret')
            expected_signature = hmac.new(
                secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"CSRF token validation failed: {e}")
            return False
    
    async def _log_security_event(
        self,
        threat_type: ThreatType,
        severity: SecurityLevel,
        source_ip: str,
        description: str,
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Log security event"""
        try:
            event = SecurityEvent(
                event_id=secrets.token_hex(16),
                threat_type=threat_type,
                severity=severity,
                timestamp=datetime.now(),
                source_ip=source_ip,
                user_id=user_id,
                description=description,
                metadata=metadata
            )
            
            # Add to in-memory storage
            self.security_events.append(event)
            
            # Trim if too many events
            if len(self.security_events) > self.max_events:
                self.security_events = self.security_events[-self.max_events:]
            
            # Store in Redis for persistence
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.lpush,
                    "security_events",
                    json.dumps(asdict(event), default=str)
                )
                
                # Keep only recent events
                await asyncio.to_thread(
                    self.redis_client.ltrim,
                    "security_events",
                    0, self.max_events - 1
                )
            
            # Log critical events immediately
            if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                logger.warning(f"SECURITY ALERT: {threat_type.value} - {description}")
            
        except Exception as e:
            logger.error(f"Security event logging failed: {e}")
    
    async def _load_blocked_ips(self):
        """Load blocked IPs from Redis"""
        try:
            if self.redis_client:
                blocked_ips = await asyncio.to_thread(
                    self.redis_client.smembers, "blocked_ips"
                )
                self.blocked_ips.update(blocked_ips)
                
                logger.info(f"Loaded {len(self.blocked_ips)} blocked IPs")
                
        except Exception as e:
            logger.error(f"Failed to load blocked IPs: {e}")
    
    async def block_ip(self, ip: str, duration_hours: int = 24, reason: str = ""):
        """Block IP address"""
        try:
            self.blocked_ips.add(ip)
            
            if self.redis_client:
                # Add to persistent blocked list
                await asyncio.to_thread(
                    self.redis_client.sadd, "blocked_ips", ip
                )
                
                # Set temporary block with expiration
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"blocked_ip:{ip}",
                    duration_hours * 3600,
                    json.dumps({
                        'blocked_at': datetime.now().isoformat(),
                        'duration_hours': duration_hours,
                        'reason': reason
                    })
                )
            
            await self._log_security_event(
                ThreatType.UNAUTHORIZED_ACCESS,
                SecurityLevel.HIGH,
                ip,
                f"IP blocked: {reason}",
                {"duration_hours": duration_hours, "reason": reason}
            )
            
            logger.warning(f"IP {ip} blocked for {duration_hours} hours: {reason}")
            
        except Exception as e:
            logger.error(f"IP blocking failed: {e}")
    
    async def _security_monitor(self):
        """Continuous security monitoring"""
        while True:
            try:
                # Check for suspicious patterns in recent events
                await self._analyze_security_events()
                
                # Clean up old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Security monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _analyze_security_events(self):
        """Analyze recent security events for patterns"""
        try:
            if not self.security_events:
                return
            
            # Analyze last hour of events
            recent_time = datetime.now() - timedelta(hours=1)
            recent_events = [
                event for event in self.security_events 
                if event.timestamp > recent_time
            ]
            
            # Check for DDoS patterns
            ip_counts = {}
            for event in recent_events:
                ip_counts[event.source_ip] = ip_counts.get(event.source_ip, 0) + 1
            
            # Block IPs with excessive requests
            for ip, count in ip_counts.items():
                if count > 100:  # 100+ events in an hour
                    await self.block_ip(ip, 2, f"Excessive security events: {count}")
            
        except Exception as e:
            logger.error(f"Security event analysis failed: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old security data"""
        try:
            # Clean old failed login attempts
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for identifier in list(self.failed_login_attempts.keys()):
                self.failed_login_attempts[identifier] = [
                    attempt for attempt in self.failed_login_attempts[identifier]
                    if attempt > cutoff_time
                ]
                
                # Remove empty entries
                if not self.failed_login_attempts[identifier]:
                    del self.failed_login_attempts[identifier]
            
        except Exception as e:
            logger.error(f"Security data cleanup failed: {e}")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get overall security status"""
        recent_time = datetime.now() - timedelta(hours=24)
        recent_events = [
            event for event in self.security_events 
            if event.timestamp > recent_time
        ]
        
        threat_counts = {}
        for event in recent_events:
            threat_type = event.threat_type.value
            threat_counts[threat_type] = threat_counts.get(threat_type, 0) + 1
        
        return {
            'total_blocked_ips': len(self.blocked_ips),
            'recent_events_24h': len(recent_events),
            'threat_breakdown': threat_counts,
            'failed_login_attempts': len(self.failed_login_attempts),
            'active_api_keys': len(self.api_keys),
            'security_level': self._calculate_security_level()
        }
    
    def _calculate_security_level(self) -> str:
        """Calculate current security threat level"""
        recent_time = datetime.now() - timedelta(hours=1)
        recent_events = [
            event for event in self.security_events 
            if event.timestamp > recent_time
        ]
        
        critical_events = [
            event for event in recent_events 
            if event.severity == SecurityLevel.CRITICAL
        ]
        
        high_events = [
            event for event in recent_events 
            if event.severity == SecurityLevel.HIGH
        ]
        
        if len(critical_events) > 5:
            return "CRITICAL"
        elif len(high_events) > 10:
            return "HIGH"
        elif len(recent_events) > 50:
            return "ELEVATED"
        else:
            return "NORMAL"
    
    async def cleanup(self):
        """Cleanup security service"""
        try:
            if self._monitoring_task:
                self._monitoring_task.cancel()
            
            if self.redis_client:
                await asyncio.to_thread(self.redis_client.close)
            
            logger.info("Security service cleanup completed")
            
        except Exception as e:
            logger.error(f"Security cleanup error: {e}")

# Global security service instance
security_service = SecurityService()