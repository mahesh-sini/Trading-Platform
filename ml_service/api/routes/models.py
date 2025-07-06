from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from services.ml_engine import ml_engine, ModelType, PredictionTimeframe
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class ModelTrainingRequest(BaseModel):
    symbol: str
    timeframe: str
    model_type: str
    training_data_days: int = 365
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['intraday', 'swing', 'long_term']
        if v not in valid_timeframes:
            raise ValueError(f'Timeframe must be one of: {valid_timeframes}')
        return v
    
    @validator('model_type')
    def validate_model_type(cls, v):
        valid_types = ['lstm', 'gru', 'random_forest', 'xgboost']
        if v not in valid_types:
            raise ValueError(f'Model type must be one of: {valid_types}')
        return v

class ModelInfo(BaseModel):
    model_id: str
    symbol: str
    timeframe: str
    model_type: str
    version: str
    is_trained: bool
    performance_metrics: Dict[str, float]
    created_at: str
    last_updated: str

@router.get("/list", response_model=List[ModelInfo])
async def list_models(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    model_type: Optional[str] = None
):
    """List available models"""
    try:
        models_info = []
        
        for model_key, model in ml_engine.models.items():
            # Apply filters
            if symbol and model.symbol.upper() != symbol.upper():
                continue
            if timeframe and model.timeframe.value != timeframe:
                continue
            if model_type and model.model_type.value != model_type:
                continue
            
            models_info.append(ModelInfo(
                model_id=model_key,
                symbol=model.symbol,
                timeframe=model.timeframe.value,
                model_type=model.model_type.value,
                version=model.version,
                is_trained=model.is_trained,
                performance_metrics=model.performance_metrics,
                created_at=datetime.utcnow().isoformat() + "Z",
                last_updated=datetime.utcnow().isoformat() + "Z"
            ))
        
        return models_info
        
    except Exception as e:
        logger.error(f"Failed to list models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve models list"
        )

@router.post("/train")
async def train_model(
    request: ModelTrainingRequest,
    background_tasks: BackgroundTasks
):
    """Train a new model"""
    try:
        # Get real training data from data service
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                # Request historical data for training
                response = await client.get(
                    f"http://localhost:8002/v1/market-data/{request.symbol}/history",
                    params={
                        "period": f"{request.training_data_days}d",
                        "interval": "1d"
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to get training data: {response.status_code}"
                    )
                
                history_data = response.json()
                if not history_data.get('data'):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No historical data available for {request.symbol}"
                    )
                
                training_data = pd.DataFrame(history_data['data'])
                
                # Ensure required columns exist
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in training_data.columns]
                if missing_columns:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Missing required columns: {missing_columns}"
                    )
                
                if len(training_data) < 100:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Insufficient data for training. Got {len(training_data)} records, need at least 100"
                    )
                
                logger.info(f"Retrieved {len(training_data)} records for training {request.symbol}")
                
            except httpx.RequestError as e:
                logger.error(f"Failed to connect to data service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Data service unavailable"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get training data: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve training data"
                )
        
        # Start training in background
        background_tasks.add_task(
            train_model_background,
            request.symbol,
            request.timeframe,
            request.model_type,
            training_data
        )
        
        return {
            "message": "Model training started",
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "model_type": request.model_type,
            "status": "training"
        }
        
    except Exception as e:
        logger.error(f"Failed to start model training: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start model training"
        )

@router.get("/{model_id}/performance")
async def get_model_performance(model_id: str):
    """Get detailed performance metrics for a specific model"""
    try:
        if model_id not in ml_engine.models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        model = ml_engine.models[model_id]
        
        return {
            "model_id": model_id,
            "symbol": model.symbol,
            "timeframe": model.timeframe.value,
            "model_type": model.model_type.value,
            "performance_metrics": model.performance_metrics,
            "is_trained": model.is_trained,
            "version": model.version
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model performance"
        )

@router.delete("/{model_id}")
async def delete_model(model_id: str):
    """Delete a model"""
    try:
        if model_id not in ml_engine.models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found"
            )
        
        # Remove from memory
        del ml_engine.models[model_id]
        
        # TODO: Remove model files from disk
        
        return {"message": f"Model {model_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete model"
        )

@router.get("/comparison")
async def compare_models(
    symbol: str,
    timeframe: str,
    metric: str = "directional_accuracy"
):
    """Compare performance of different models for a symbol/timeframe"""
    try:
        comparison_data = []
        
        for model_type in ModelType:
            model_key = f"{symbol.upper()}_{timeframe}_{model_type.value}"
            if model_key in ml_engine.models:
                model = ml_engine.models[model_key]
                comparison_data.append({
                    "model_type": model_type.value,
                    "metric_value": model.performance_metrics.get(metric, 0),
                    "is_trained": model.is_trained,
                    "version": model.version
                })
        
        # Sort by metric value
        comparison_data.sort(key=lambda x: x["metric_value"], reverse=True)
        
        return {
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "comparison_metric": metric,
            "models": comparison_data
        }
        
    except Exception as e:
        logger.error(f"Model comparison failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Model comparison failed"
        )

@router.get("/status")
async def get_models_status():
    """Get overall status of ML models"""
    try:
        total_models = len(ml_engine.models)
        trained_models = sum(1 for model in ml_engine.models.values() if model.is_trained)
        
        model_types_count = {}
        timeframes_count = {}
        
        for model in ml_engine.models.values():
            model_types_count[model.model_type.value] = model_types_count.get(model.model_type.value, 0) + 1
            timeframes_count[model.timeframe.value] = timeframes_count.get(model.timeframe.value, 0) + 1
        
        return {
            "total_models": total_models,
            "trained_models": trained_models,
            "untrained_models": total_models - trained_models,
            "model_types_distribution": model_types_count,
            "timeframes_distribution": timeframes_count,
            "status": "healthy" if trained_models > 0 else "no_trained_models"
        }
        
    except Exception as e:
        logger.error(f"Failed to get models status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get models status"
        )

# Background task functions
async def train_model_background(symbol: str, timeframe: str, model_type: str, data: pd.DataFrame):
    """Background task for model training"""
    try:
        import numpy as np
        
        logger.info(f"Starting background training for {symbol} {timeframe} {model_type}")
        
        performance = await ml_engine.train_model(
            symbol=symbol,
            timeframe=PredictionTimeframe(timeframe),
            model_type=ModelType(model_type),
            data=data
        )
        
        logger.info(f"Model training completed: {symbol} {timeframe} {model_type}")
        logger.info(f"Performance: {performance}")
        
    except Exception as e:
        logger.error(f"Background model training failed: {str(e)}")