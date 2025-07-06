"""
Admin System Configuration API
Centralized management of all system-level APIs and configurations
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import relationship
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
from cryptography.fernet import Fernet
import base64

from ...services.database import get_db
from ...models.admin import Admin
from ...models.system_config import (
    SystemAPIConfig, SystemFeatureConfig, APIHealthCheck, APIUsageLog,
    SystemNotification, APIProviderEnum, APIStatusEnum
)
from ...utils.logging_config import get_logger
from .admin import get_current_admin, require_permission, _log_admin_action

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/system-config", tags=["admin-system-config"])


class EncryptionService:
    """Service for encrypting/decrypting sensitive API credentials"""
    
    def __init__(self):
        # In production, this should come from environment variables
        self.key = base64.urlsafe_b64encode(b"32-char-secret-for-api-encryption")
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not data:
            return ""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not encrypted_data:
            return ""
        return self.cipher.decrypt(encrypted_data.encode()).decode()


encryption_service = EncryptionService()


# System API Configuration Endpoints
@router.get("/apis")
@require_permission("VIEW_SYSTEM_CONFIG")
async def get_system_apis(
    provider: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all system API configurations"""
    
    query = db.query(SystemAPIConfig)
    
    # Apply filters
    if provider:
        query = query.filter(SystemAPIConfig.provider == provider)
    
    if status:
        query = query.filter(SystemAPIConfig.status == status)
    
    # Group by category for better organization
    apis = query.order_by(SystemAPIConfig.provider).all()
    
    # Organize APIs by category
    categorized_apis = {
        "market_data": [],
        "news_sentiment": [],
        "ai_ml": [],
        "communication": [],
        "infrastructure": [],
        "monitoring": []
    }
    
    for api in apis:
        # Decrypt credentials for display (mask sensitive parts)
        api_data = {
            "id": str(api.id),
            "provider": api.provider.value,
            "display_name": api.display_name,
            "description": api.description,
            "status": api.status.value,
            "is_enabled": api.is_enabled,
            "base_url": api.base_url,
            "rate_limit_per_minute": api.rate_limit_per_minute,
            "last_health_check": api.last_health_check.isoformat() if api.last_health_check else None,
            "requests_today": api.requests_today,
            "success_rate": api.success_rate,
            "monthly_cost": api.monthly_cost,
            "plan_type": api.plan_type,
            "features_enabled": api.features_enabled,
            # Mask credentials for security
            "has_api_key": bool(api.api_key),
            "has_secret_key": bool(api.secret_key),
            "api_key_preview": mask_credential(encryption_service.decrypt(api.api_key) if api.api_key else ""),
            "configured_by": api.configured_by_admin.username if api.configured_by_admin else None,
            "last_modified": api.updated_at.isoformat() if api.updated_at else None
        }
        
        # Categorize API
        category = get_api_category(api.provider)
        if category in categorized_apis:
            categorized_apis[category].append(api_data)
    
    return {
        "apis_by_category": categorized_apis,
        "total_apis": len(apis),
        "active_apis": len([api for api in apis if api.is_enabled]),
        "health_summary": calculate_health_summary(apis)
    }


@router.get("/apis/{api_id}")
@require_permission("VIEW_SYSTEM_CONFIG")
async def get_api_details(
    api_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific API configuration"""
    
    api = db.query(SystemAPIConfig).filter(SystemAPIConfig.id == api_id).first()
    if not api:
        raise HTTPException(status_code=404, detail="API configuration not found")
    
    # Get recent health checks
    recent_health_checks = db.query(APIHealthCheck).filter(
        APIHealthCheck.api_config_id == api_id
    ).order_by(desc(APIHealthCheck.created_at)).limit(10).all()
    
    # Get usage statistics
    today = datetime.utcnow().date()
    usage_stats = db.query(APIUsageLog).filter(
        and_(
            APIUsageLog.api_config_id == api_id,
            func.date(APIUsageLog.created_at) == today
        )
    ).all()
    
    return {
        "api": {
            "id": str(api.id),
            "provider": api.provider.value,
            "display_name": api.display_name,
            "description": api.description,
            "base_url": api.base_url,
            "status": api.status.value,
            "is_enabled": api.is_enabled,
            "rate_limit_per_minute": api.rate_limit_per_minute,
            "rate_limit_per_day": api.rate_limit_per_day,
            "timeout_seconds": api.timeout_seconds,
            "plan_type": api.plan_type,
            "monthly_request_limit": api.monthly_request_limit,
            "requests_remaining": api.requests_remaining,
            "features_enabled": api.features_enabled,
            "monthly_cost": api.monthly_cost,
            "usage_cost_today": api.usage_cost_today,
            # Credentials (decrypted for authorized viewing)
            "api_key": encryption_service.decrypt(api.api_key) if api.api_key else "",
            "secret_key": encryption_service.decrypt(api.secret_key) if api.secret_key else "",
            "access_token": encryption_service.decrypt(api.access_token) if api.access_token else "",
            "additional_config": api.additional_config,
            "configured_by": api.configured_by_admin.username if api.configured_by_admin else None,
            "last_modified": api.updated_at.isoformat() if api.updated_at else None
        },
        "health_checks": [
            {
                "id": str(check.id),
                "is_healthy": check.is_healthy,
                "response_time_ms": check.response_time_ms,
                "status_code": check.status_code,
                "error_message": check.error_message,
                "checked_at": check.created_at.isoformat(),
                "check_type": check.check_type
            } for check in recent_health_checks
        ],
        "usage_today": {
            "total_requests": len(usage_stats),
            "successful_requests": len([u for u in usage_stats if u.status_code < 400]),
            "failed_requests": len([u for u in usage_stats if u.status_code >= 400]),
            "total_cost": sum(u.cost for u in usage_stats),
            "avg_response_time": sum(u.response_time_ms for u in usage_stats) / len(usage_stats) if usage_stats else 0
        }
    }


@router.post("/apis")
@require_permission("MANAGE_SYSTEM_CONFIG")
async def create_api_config(
    api_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create new API configuration"""
    
    # Validate required fields
    required_fields = ["provider", "display_name"]
    for field in required_fields:
        if field not in api_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Check if provider already exists
    existing = db.query(SystemAPIConfig).filter(
        SystemAPIConfig.provider == api_data["provider"]
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="API provider already configured")
    
    # Encrypt sensitive credentials
    encrypted_api_key = encryption_service.encrypt(api_data.get("api_key", ""))
    encrypted_secret_key = encryption_service.encrypt(api_data.get("secret_key", ""))
    encrypted_access_token = encryption_service.encrypt(api_data.get("access_token", ""))
    
    # Create API configuration
    api_config = SystemAPIConfig(
        provider=APIProviderEnum(api_data["provider"]),
        display_name=api_data["display_name"],
        description=api_data.get("description", ""),
        api_key=encrypted_api_key,
        secret_key=encrypted_secret_key,
        access_token=encrypted_access_token,
        base_url=api_data.get("base_url", ""),
        rate_limit_per_minute=api_data.get("rate_limit_per_minute", 60),
        rate_limit_per_day=api_data.get("rate_limit_per_day"),
        timeout_seconds=api_data.get("timeout_seconds", 30),
        plan_type=api_data.get("plan_type", "free"),
        monthly_request_limit=api_data.get("monthly_request_limit"),
        features_enabled=api_data.get("features_enabled", {}),
        additional_config=api_data.get("additional_config", {}),
        configured_by=current_admin.id,
        last_modified_by=current_admin.id
    )
    
    db.add(api_config)
    db.commit()
    db.refresh(api_config)
    
    # Schedule health check
    background_tasks.add_task(perform_health_check, str(api_config.id))
    
    _log_admin_action(
        db, current_admin,
        "API_CONFIG_CREATED",
        f"Created API configuration for {api_data['provider']}",
        resource_id=str(api_config.id),
        after_state={"provider": api_data["provider"], "display_name": api_data["display_name"]}
    )
    
    return {
        "success": True,
        "message": "API configuration created successfully",
        "api_id": str(api_config.id)
    }


@router.put("/apis/{api_id}")
@require_permission("MANAGE_SYSTEM_CONFIG")
async def update_api_config(
    api_id: str,
    api_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update API configuration"""
    
    api_config = db.query(SystemAPIConfig).filter(SystemAPIConfig.id == api_id).first()
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")
    
    # Store old state for audit
    old_state = {
        "display_name": api_config.display_name,
        "is_enabled": api_config.is_enabled,
        "base_url": api_config.base_url,
        "rate_limit_per_minute": api_config.rate_limit_per_minute
    }
    
    # Update fields
    updateable_fields = [
        "display_name", "description", "base_url", "rate_limit_per_minute",
        "rate_limit_per_day", "timeout_seconds", "plan_type", "monthly_request_limit",
        "features_enabled", "additional_config", "is_enabled"
    ]
    
    for field in updateable_fields:
        if field in api_data:
            setattr(api_config, field, api_data[field])
    
    # Update credentials if provided
    if "api_key" in api_data:
        api_config.api_key = encryption_service.encrypt(api_data["api_key"])
    
    if "secret_key" in api_data:
        api_config.secret_key = encryption_service.encrypt(api_data["secret_key"])
    
    if "access_token" in api_data:
        api_config.access_token = encryption_service.encrypt(api_data["access_token"])
    
    api_config.last_modified_by = current_admin.id
    api_config.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Schedule health check if enabled
    if api_config.is_enabled:
        background_tasks.add_task(perform_health_check, api_id)
    
    _log_admin_action(
        db, current_admin,
        "API_CONFIG_UPDATED",
        f"Updated API configuration for {api_config.provider.value}",
        resource_id=api_id,
        before_state=old_state,
        after_state=api_data
    )
    
    return {"success": True, "message": "API configuration updated successfully"}


@router.delete("/apis/{api_id}")
@require_permission("MANAGE_SYSTEM_CONFIG")
async def delete_api_config(
    api_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete API configuration"""
    
    api_config = db.query(SystemAPIConfig).filter(SystemAPIConfig.id == api_id).first()
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")
    
    provider_name = api_config.provider.value
    
    # Check if any features depend on this API
    dependent_features = db.query(SystemFeatureConfig).filter(
        SystemFeatureConfig.required_apis.contains([api_config.provider.value])
    ).all()
    
    if dependent_features:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete API. Required by features: {[f.feature_name for f in dependent_features]}"
        )
    
    db.delete(api_config)
    db.commit()
    
    _log_admin_action(
        db, current_admin,
        "API_CONFIG_DELETED",
        f"Deleted API configuration for {provider_name}",
        resource_id=api_id
    )
    
    return {"success": True, "message": "API configuration deleted successfully"}


@router.post("/apis/{api_id}/test")
@require_permission("MANAGE_SYSTEM_CONFIG")
async def test_api_connection(
    api_id: str,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Test API connection and health"""
    
    api_config = db.query(SystemAPIConfig).filter(SystemAPIConfig.id == api_id).first()
    if not api_config:
        raise HTTPException(status_code=404, detail="API configuration not found")
    
    # Perform health check
    health_result = await perform_health_check(api_id, current_admin.id)
    
    _log_admin_action(
        db, current_admin,
        "API_CONNECTION_TESTED",
        f"Tested connection for {api_config.provider.value}",
        resource_id=api_id,
        after_state=health_result
    )
    
    return health_result


# System Features Management
@router.get("/features")
@require_permission("VIEW_SYSTEM_CONFIG")
async def get_system_features(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all system features and their configurations"""
    
    features = db.query(SystemFeatureConfig).order_by(
        SystemFeatureConfig.category, SystemFeatureConfig.priority.desc()
    ).all()
    
    # Group by category
    categorized_features = {}
    for feature in features:
        category = feature.category or "general"
        if category not in categorized_features:
            categorized_features[category] = []
        
        # Check if all required APIs are configured and healthy
        api_status = check_feature_api_requirements(db, feature)
        
        categorized_features[category].append({
            "id": str(feature.id),
            "feature_name": feature.feature_name,
            "display_name": feature.display_name,
            "description": feature.description,
            "is_enabled": feature.is_enabled,
            "required_apis": feature.required_apis,
            "optional_apis": feature.optional_apis,
            "api_status": api_status,
            "can_enable": api_status["all_required_healthy"],
            "config_values": feature.config_values,
            "priority": feature.priority
        })
    
    return {
        "features_by_category": categorized_features,
        "total_features": len(features),
        "enabled_features": len([f for f in features if f.is_enabled])
    }


@router.put("/features/{feature_name}")
@require_permission("MANAGE_SYSTEM_CONFIG")
async def update_system_feature(
    feature_name: str,
    feature_data: Dict[str, Any],
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update system feature configuration"""
    
    feature = db.query(SystemFeatureConfig).filter(
        SystemFeatureConfig.feature_name == feature_name
    ).first()
    
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Check API requirements if enabling feature
    if feature_data.get("is_enabled", False):
        api_status = check_feature_api_requirements(db, feature)
        if not api_status["all_required_healthy"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot enable feature. Missing or unhealthy APIs: {api_status['missing_apis']}"
            )
    
    old_state = {
        "is_enabled": feature.is_enabled,
        "config_values": feature.config_values
    }
    
    # Update feature
    if "is_enabled" in feature_data:
        feature.is_enabled = feature_data["is_enabled"]
    
    if "config_values" in feature_data:
        feature.config_values = feature_data["config_values"]
    
    feature.last_modified_by = current_admin.id
    feature.updated_at = datetime.utcnow()
    
    db.commit()
    
    _log_admin_action(
        db, current_admin,
        "SYSTEM_FEATURE_UPDATED",
        f"Updated feature: {feature_name}",
        resource_id=str(feature.id),
        before_state=old_state,
        after_state=feature_data
    )
    
    return {"success": True, "message": "Feature updated successfully"}


# Health Monitoring
@router.get("/health/overview")
@require_permission("VIEW_SYSTEM_CONFIG")
async def get_health_overview(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get overall system health overview"""
    
    # Get all APIs
    apis = db.query(SystemAPIConfig).filter(SystemAPIConfig.is_enabled == True).all()
    
    # Get recent health checks (last 24 hours)
    recent_checks = db.query(APIHealthCheck).filter(
        APIHealthCheck.created_at > datetime.utcnow() - timedelta(hours=24)
    ).all()
    
    # Calculate health metrics
    total_apis = len(apis)
    healthy_apis = len([api for api in apis if api.status == APIStatusEnum.ACTIVE])
    
    # System status
    if healthy_apis == total_apis:
        system_status = "healthy"
    elif healthy_apis > total_apis * 0.7:
        system_status = "warning"
    else:
        system_status = "critical"
    
    # Get enabled features
    enabled_features = db.query(SystemFeatureConfig).filter(
        SystemFeatureConfig.is_enabled == True
    ).count()
    
    return {
        "system_status": system_status,
        "apis": {
            "total": total_apis,
            "healthy": healthy_apis,
            "unhealthy": total_apis - healthy_apis,
            "health_percentage": (healthy_apis / total_apis * 100) if total_apis > 0 else 0
        },
        "features": {
            "enabled": enabled_features,
            "available": db.query(SystemFeatureConfig).count()
        },
        "recent_activity": {
            "health_checks_24h": len(recent_checks),
            "failed_checks_24h": len([c for c in recent_checks if not c.is_healthy])
        }
    }


# Utility Functions
def mask_credential(credential: str) -> str:
    """Mask credential for display purposes"""
    if not credential or len(credential) < 8:
        return "••••••••"
    return credential[:4] + "••••••••" + credential[-4:]


def get_api_category(provider: APIProviderEnum) -> str:
    """Get category for API provider"""
    market_data_providers = [
        APIProviderEnum.ALPHA_VANTAGE, APIProviderEnum.POLYGON, APIProviderEnum.YAHOO_FINANCE,
        APIProviderEnum.FINNHUB, APIProviderEnum.IEX_CLOUD, APIProviderEnum.NSE_OFFICIAL, APIProviderEnum.BSE_OFFICIAL
    ]
    
    news_providers = [
        APIProviderEnum.NEWS_API, APIProviderEnum.TWITTER_API, APIProviderEnum.REDDIT_API,
        APIProviderEnum.ECONOMIC_TIMES, APIProviderEnum.MONEY_CONTROL
    ]
    
    ai_providers = [
        APIProviderEnum.OPENAI, APIProviderEnum.ANTHROPIC, APIProviderEnum.GOOGLE_AI, APIProviderEnum.AZURE_AI
    ]
    
    communication_providers = [
        APIProviderEnum.SENDGRID, APIProviderEnum.TWILIO, APIProviderEnum.AWS_SES,
        APIProviderEnum.SLACK, APIProviderEnum.DISCORD
    ]
    
    if provider in market_data_providers:
        return "market_data"
    elif provider in news_providers:
        return "news_sentiment"
    elif provider in ai_providers:
        return "ai_ml"
    elif provider in communication_providers:
        return "communication"
    else:
        return "infrastructure"


def calculate_health_summary(apis: List[SystemAPIConfig]) -> Dict[str, Any]:
    """Calculate health summary for APIs"""
    if not apis:
        return {"overall_health": 0, "healthy_count": 0, "total_count": 0}
    
    healthy_count = len([api for api in apis if api.status == APIStatusEnum.ACTIVE])
    total_count = len(apis)
    
    return {
        "overall_health": (healthy_count / total_count * 100) if total_count > 0 else 0,
        "healthy_count": healthy_count,
        "total_count": total_count,
        "unhealthy_count": total_count - healthy_count
    }


def check_feature_api_requirements(db: Session, feature: SystemFeatureConfig) -> Dict[str, Any]:
    """Check if feature's API requirements are met"""
    required_apis = feature.required_apis or []
    
    if not required_apis:
        return {"all_required_healthy": True, "missing_apis": [], "unhealthy_apis": []}
    
    missing_apis = []
    unhealthy_apis = []
    
    for api_provider in required_apis:
        api_config = db.query(SystemAPIConfig).filter(
            SystemAPIConfig.provider == api_provider,
            SystemAPIConfig.is_enabled == True
        ).first()
        
        if not api_config:
            missing_apis.append(api_provider)
        elif api_config.status != APIStatusEnum.ACTIVE:
            unhealthy_apis.append(api_provider)
    
    return {
        "all_required_healthy": len(missing_apis) == 0 and len(unhealthy_apis) == 0,
        "missing_apis": missing_apis,
        "unhealthy_apis": unhealthy_apis
    }


async def perform_health_check(api_id: str, checked_by_id: str = None) -> Dict[str, Any]:
    """Perform health check for an API"""
    db = next(get_db())
    try:
        api_config = db.query(SystemAPIConfig).filter(SystemAPIConfig.id == api_id).first()
        if not api_config:
            return {"error": "API configuration not found"}
        
        # Basic health check implementation
        # This would be expanded based on each API provider's requirements
        test_url = api_config.health_check_url or api_config.base_url
        
        if not test_url:
            return {"error": "No health check URL configured"}
        
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=api_config.timeout_seconds)) as session:
                async with session.get(test_url) as response:
                    response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    is_healthy = response.status < 400
                    
                    # Create health check record
                    health_check = APIHealthCheck(
                        api_config_id=api_config.id,
                        is_healthy=is_healthy,
                        response_time_ms=response_time,
                        status_code=response.status,
                        test_endpoint=test_url,
                        checked_by=checked_by_id
                    )
                    
                    db.add(health_check)
                    
                    # Update API status
                    if is_healthy:
                        api_config.status = APIStatusEnum.ACTIVE
                        api_config.last_error = None
                    else:
                        api_config.status = APIStatusEnum.ERROR
                        api_config.last_error = f"HTTP {response.status}"
                    
                    api_config.last_health_check = datetime.utcnow()
                    api_config.avg_response_time = response_time
                    
                    db.commit()
                    
                    return {
                        "is_healthy": is_healthy,
                        "response_time_ms": response_time,
                        "status_code": response.status,
                        "message": "Health check completed successfully"
                    }
        
        except Exception as e:
            # Create failed health check record
            health_check = APIHealthCheck(
                api_config_id=api_config.id,
                is_healthy=False,
                error_message=str(e),
                test_endpoint=test_url,
                checked_by=checked_by_id
            )
            
            db.add(health_check)
            
            # Update API status
            api_config.status = APIStatusEnum.ERROR
            api_config.last_error = str(e)
            api_config.last_health_check = datetime.utcnow()
            
            db.commit()
            
            return {
                "is_healthy": False,
                "error_message": str(e),
                "message": "Health check failed"
            }
    
    finally:
        db.close()