"""
Model Deployment API Routes
RESTful API for model deployment, versioning, and A/B testing
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from services.model_deployment import (
    model_deployment_service, DeploymentEnvironment, ModelStatus,
    ModelVersion, ABTestConfig
)
from services.ml_engine import ModelType, PredictionTimeframe

router = APIRouter()

# Pydantic models for API
class DeployModelRequest(BaseModel):
    model_id: str = Field(..., description="Unique model identifier")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Prediction timeframe")
    model_type: str = Field(..., description="Model type")
    environment: str = Field(..., description="Deployment environment")
    performance_threshold: float = Field(0.6, description="Minimum performance threshold")

class ABTestRequest(BaseModel):
    champion_model_id: str = Field(..., description="Current champion model")
    challenger_model_id: str = Field(..., description="New challenger model")
    traffic_split: float = Field(..., ge=0, le=100, description="Traffic percentage for challenger")
    duration_days: int = Field(7, ge=1, le=30, description="Test duration in days")
    success_metric: str = Field("directional_accuracy", description="Success metric to optimize")

class PredictionRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Prediction timeframe")
    features: Dict[str, Any] = Field({}, description="Input features")
    environment: str = Field("production", description="Environment to use")

class PromoteChallengerRequest(BaseModel):
    test_id: str = Field(..., description="A/B test identifier")

@router.post("/deploy", response_model=Dict[str, Any])
async def deploy_model(request: DeployModelRequest):
    """Deploy model to specified environment"""
    try:
        # Validate enums
        try:
            environment = DeploymentEnvironment(request.environment)
            timeframe = PredictionTimeframe(request.timeframe)
            model_type = ModelType(request.model_type)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
        
        # Deploy model
        success = await model_deployment_service.deploy_model(
            model_id=request.model_id,
            symbol=request.symbol,
            timeframe=timeframe,
            model_type=model_type,
            environment=environment,
            performance_threshold=request.performance_threshold
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Model {request.model_id} deployed to {request.environment}",
                "deployment_timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Model deployment failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ab-test/start", response_model=Dict[str, Any])
async def start_ab_test(request: ABTestRequest):
    """Start A/B test between two models"""
    try:
        test_id = await model_deployment_service.start_ab_test(
            champion_model_id=request.champion_model_id,
            challenger_model_id=request.challenger_model_id,
            traffic_split=request.traffic_split,
            duration_days=request.duration_days,
            success_metric=request.success_metric
        )
        
        return {
            "status": "success",
            "test_id": test_id,
            "message": "A/B test started successfully",
            "start_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ab-test/{test_id}/evaluate", response_model=Dict[str, Any])
async def evaluate_ab_test(test_id: str):
    """Evaluate A/B test results"""
    try:
        results = await model_deployment_service.evaluate_ab_test(test_id)
        return {
            "status": "success",
            "results": results,
            "evaluation_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ab-test/promote", response_model=Dict[str, Any])
async def promote_challenger(request: PromoteChallengerRequest):
    """Promote challenger to champion after successful A/B test"""
    try:
        success = await model_deployment_service.promote_challenger(request.test_id)
        
        if success:
            return {
                "status": "success",
                "message": "Challenger promoted to champion",
                "promotion_timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to promote challenger")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict", response_model=Dict[str, Any])
async def predict_with_deployment(request: PredictionRequest):
    """Make prediction using deployed models with A/B testing"""
    try:
        # Validate parameters
        try:
            timeframe = PredictionTimeframe(request.timeframe)
            environment = DeploymentEnvironment(request.environment)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {str(e)}")
        
        # Make prediction
        result = await model_deployment_service.predict_with_deployment(
            symbol=request.symbol,
            timeframe=timeframe,
            features=request.features,
            environment=environment
        )
        
        return {
            "status": "success",
            "prediction": {
                "symbol": result.symbol,
                "predicted_price": result.predicted_price,
                "current_price": result.current_price,
                "predicted_direction": result.predicted_direction,
                "confidence_score": result.confidence_score,
                "model_version": result.model_version,
                "features_used": result.features_used,
                "prediction_horizon": result.prediction_horizon,
                "created_at": result.created_at.isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rollback/{model_id}", response_model=Dict[str, Any])
async def rollback_deployment(model_id: str):
    """Rollback to previous model version"""
    try:
        success = await model_deployment_service.rollback_deployment(model_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Model {model_id} rolled back successfully",
                "rollback_timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Rollback failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=Dict[str, Any])
async def get_deployment_status():
    """Get overall deployment status"""
    try:
        status = model_deployment_service.get_deployment_status()
        return {
            "status": "success",
            "deployment_status": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=Dict[str, Any])
async def list_deployed_models(environment: Optional[str] = None):
    """List deployed models"""
    try:
        models = []
        
        for model_id, model_version in model_deployment_service.model_versions.items():
            # Filter by environment if specified
            if environment and model_version.environment.value != environment:
                continue
            
            models.append({
                "model_id": model_id,
                "version": model_version.version,
                "environment": model_version.environment.value,
                "status": model_version.status.value,
                "deployed_at": model_version.deployed_at.isoformat(),
                "champion_model": model_version.champion_model,
                "traffic_percentage": model_version.traffic_percentage,
                "health_status": model_version.health_status,
                "performance_metrics": model_version.performance_metrics,
                "prediction_count": model_version.prediction_count,
                "error_count": model_version.error_count,
                "avg_latency": model_version.avg_latency
            })
        
        return {
            "status": "success",
            "models": models,
            "total_count": len(models),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ab-tests", response_model=Dict[str, Any])
async def list_ab_tests(active_only: bool = False):
    """List A/B tests"""
    try:
        tests = []
        current_time = datetime.now()
        
        for test_id, ab_test in model_deployment_service.ab_tests.items():
            # Filter active tests if requested
            if active_only and not (ab_test.start_date <= current_time <= ab_test.end_date):
                continue
            
            tests.append({
                "test_id": test_id,
                "champion_model": ab_test.champion_model,
                "challenger_model": ab_test.challenger_model,
                "traffic_split": ab_test.traffic_split,
                "start_date": ab_test.start_date.isoformat(),
                "end_date": ab_test.end_date.isoformat(),
                "success_metric": ab_test.success_metric,
                "min_sample_size": ab_test.min_sample_size,
                "confidence_level": ab_test.confidence_level,
                "is_active": ab_test.start_date <= current_time <= ab_test.end_date
            })
        
        return {
            "status": "success",
            "ab_tests": tests,
            "total_count": len(tests),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", response_model=Dict[str, Any])
async def deployment_health_check():
    """Health check for deployment service"""
    try:
        status = model_deployment_service.get_deployment_status()
        
        # Determine overall health
        healthy_count = status.get('healthy_models', 0)
        error_count = status.get('error_models', 0)
        total_count = status.get('total_deployments', 0)
        
        if total_count == 0:
            health_status = "no_deployments"
        elif error_count == 0:
            health_status = "healthy"
        elif error_count < healthy_count:
            health_status = "degraded"
        else:
            health_status = "unhealthy"
        
        return {
            "status": "success",
            "health_status": health_status,
            "deployment_stats": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "health_status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }