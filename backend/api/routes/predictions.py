"""
Predictions API Routes - Proxy to ML Service
Routes predictions requests to the dedicated ML microservice
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from services.database import get_db
from typing import Dict, Any, Optional
import httpx
import logging
import os
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()

# ML Service configuration
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")

class PredictionRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field("intraday", description="Prediction timeframe")
    features: Dict[str, Any] = Field({}, description="Input features")
    horizon: str = Field("1d", description="Prediction horizon")

class ModelDeploymentRequest(BaseModel):
    model_id: str = Field(..., description="Model identifier")
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Timeframe")
    model_type: str = Field(..., description="Model type")
    environment: str = Field("development", description="Environment")

@router.post("/generate")
async def generate_prediction(
    request: PredictionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate new prediction via ML service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/v1/predictions/predict",
                json={
                    "symbol": request.symbol,
                    "timeframe": request.timeframe,
                    "horizon": request.horizon,
                    "features": request.features
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML service error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ML service error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ML service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"ML service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service unavailable"
        )

@router.post("/production/predict")
async def production_prediction(
    request: PredictionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate prediction using production ML deployment"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/v1/deployment/predict",
                json={
                    "symbol": request.symbol,
                    "timeframe": request.timeframe,
                    "features": request.features,
                    "environment": "production"
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML deployment error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ML deployment error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ML service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"ML service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service unavailable"
        )

@router.get("")
async def get_predictions(
    symbol: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get recent predictions from ML service"""
    try:
        params = {"limit": limit}
        if symbol:
            params["symbol"] = symbol
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ML_SERVICE_URL}/v1/predictions/history",
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML service error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ML service error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ML service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"ML service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service unavailable"
        )

@router.get("/performance")
async def get_model_performance(
    model_id: Optional[str] = None,
    environment: str = "production",
    db: AsyncSession = Depends(get_db)
):
    """Get model performance metrics from ML service"""
    try:
        params = {"environment": environment}
        if model_id:
            params["model_id"] = model_id
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ML_SERVICE_URL}/v1/deployment/models",
                params=params,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML service error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ML service error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ML service timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"ML service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service unavailable"
        )

@router.post("/deploy")
async def deploy_model(
    request: ModelDeploymentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Deploy model via ML service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ML_SERVICE_URL}/v1/deployment/deploy",
                json={
                    "model_id": request.model_id,
                    "symbol": request.symbol,
                    "timeframe": request.timeframe,
                    "model_type": request.model_type,
                    "environment": request.environment
                },
                timeout=60.0  # Deployment can take longer
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML deployment error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ML deployment error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="ML deployment timeout"
        )
    except httpx.RequestError as e:
        logger.error(f"ML service connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service unavailable"
        )

@router.get("/health")
async def ml_service_health():
    """Check ML service health"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ML_SERVICE_URL}/health",
                timeout=10.0
            )
            
            if response.status_code == 200:
                ml_health = response.json()
                return {
                    "status": "healthy",
                    "ml_service": ml_health,
                    "proxy_status": "operational"
                }
            else:
                return {
                    "status": "unhealthy",
                    "ml_service": {"status": "error", "code": response.status_code},
                    "proxy_status": "operational"
                }
                
    except httpx.RequestError as e:
        logger.error(f"ML service health check failed: {e}")
        return {
            "status": "unhealthy",
            "ml_service": {"status": "unreachable", "error": str(e)},
            "proxy_status": "operational"
        }