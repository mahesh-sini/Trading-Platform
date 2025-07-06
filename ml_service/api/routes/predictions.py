from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from services.ml_engine import ml_engine, PredictionRequest, PredictionTimeframe
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class PredictionRequestModel(BaseModel):
    symbol: str
    timeframe: str
    prediction_horizon: str = "1d"
    custom_features: Optional[Dict[str, Any]] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v or len(v) < 1:
            raise ValueError('Symbol is required')
        return v.upper()
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['intraday', 'swing', 'long_term']
        if v not in valid_timeframes:
            raise ValueError(f'Timeframe must be one of: {valid_timeframes}')
        return v

class PredictionResponse(BaseModel):
    prediction_id: str
    symbol: str
    predicted_price: float
    current_price: float
    predicted_direction: str
    confidence_score: float
    prediction_horizon: str
    model_version: str
    features_used: List[str]
    created_at: str
    expires_at: str

class BatchPredictionRequest(BaseModel):
    symbols: List[str]
    timeframe: str
    prediction_horizon: str = "1d"
    
    @validator('symbols')
    def validate_symbols(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one symbol is required')
        if len(v) > 50:
            raise ValueError('Maximum 50 symbols allowed')
        return [symbol.upper() for symbol in v]

@router.post("/generate", response_model=PredictionResponse)
async def generate_prediction(
    request: PredictionRequestModel,
    background_tasks: BackgroundTasks
):
    """Generate a new AI prediction for a symbol"""
    try:
        # Create prediction request
        prediction_request = PredictionRequest(
            symbol=request.symbol,
            timeframe=PredictionTimeframe(request.timeframe),
            horizon=request.prediction_horizon,
            features=request.custom_features
        )
        
        # Generate prediction
        result = await ml_engine.predict(prediction_request)
        
        # Calculate expiry time based on horizon
        from datetime import timedelta
        horizon_hours = {"1h": 1, "4h": 4, "1d": 24, "7d": 168}.get(request.prediction_horizon, 24)
        expires_at = datetime.utcnow() + timedelta(hours=horizon_hours)
        
        return PredictionResponse(
            prediction_id=str(hash(f"{result.symbol}_{result.created_at}")),
            symbol=result.symbol,
            predicted_price=result.predicted_price,
            current_price=result.current_price,
            predicted_direction=result.predicted_direction,
            confidence_score=result.confidence_score,
            prediction_horizon=result.prediction_horizon,
            model_version=result.model_version,
            features_used=result.features_used,
            created_at=result.created_at.isoformat(),
            expires_at=expires_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Prediction generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction generation failed: {str(e)}"
        )

@router.post("/batch", response_model=List[PredictionResponse])
async def generate_batch_predictions(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks
):
    """Generate predictions for multiple symbols"""
    try:
        predictions = []
        
        for symbol in request.symbols:
            try:
                prediction_request = PredictionRequest(
                    symbol=symbol,
                    timeframe=PredictionTimeframe(request.timeframe),
                    horizon=request.prediction_horizon
                )
                
                result = await ml_engine.predict(prediction_request)
                
                # Calculate expiry time
                from datetime import timedelta
                horizon_hours = {"1h": 1, "4h": 4, "1d": 24, "7d": 168}.get(request.prediction_horizon, 24)
                expires_at = datetime.utcnow() + timedelta(hours=horizon_hours)
                
                predictions.append(PredictionResponse(
                    prediction_id=str(hash(f"{result.symbol}_{result.created_at}")),
                    symbol=result.symbol,
                    predicted_price=result.predicted_price,
                    current_price=result.current_price,
                    predicted_direction=result.predicted_direction,
                    confidence_score=result.confidence_score,
                    prediction_horizon=result.prediction_horizon,
                    model_version=result.model_version,
                    features_used=result.features_used,
                    created_at=result.created_at.isoformat(),
                    expires_at=expires_at.isoformat()
                ))
                
            except Exception as e:
                logger.error(f"Failed to generate prediction for {symbol}: {str(e)}")
                # Continue with other symbols
                continue
        
        return predictions
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch prediction failed"
        )

@router.get("/performance")
async def get_model_performance(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    model_type: Optional[str] = None
):
    """Get model performance metrics"""
    try:
        if symbol and timeframe:
            performance = await ml_engine.get_model_performance(symbol, timeframe)
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "performance": performance
            }
        else:
            # Return overall performance summary
            return {
                "message": "Model performance endpoint - specify symbol and timeframe for detailed metrics",
                "available_timeframes": ["intraday", "swing", "long_term"],
                "available_models": ["lstm", "gru", "random_forest", "xgboost", "ensemble"]
            }
            
    except Exception as e:
        logger.error(f"Failed to get model performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve model performance"
        )

@router.get("/status")
async def get_prediction_service_status():
    """Get prediction service status"""
    try:
        # Check if models are loaded
        model_count = len(ml_engine.models)
        
        return {
            "status": "healthy",
            "models_loaded": model_count,
            "service_uptime": "running",
            "last_training": "not implemented",
            "next_retrain": "not scheduled"
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status check failed"
        )

@router.post("/retrain")
async def trigger_model_retraining(
    background_tasks: BackgroundTasks,
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None
):
    """Trigger model retraining"""
    try:
        # Add retraining task to background
        background_tasks.add_task(ml_engine.retrain_models)
        
        return {
            "message": "Model retraining triggered",
            "status": "scheduled",
            "target_symbol": symbol,
            "target_timeframe": timeframe
        }
        
    except Exception as e:
        logger.error(f"Retrain trigger failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger retraining"
        )