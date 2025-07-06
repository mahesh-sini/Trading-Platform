"""
Machine Learning Predictions API
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.services.ml.prediction_models import (
    ml_prediction_service, ModelConfig, ModelType, PredictionTarget
)
from app.services.ml.training_pipeline import (
    training_pipeline, TrainingJob, DataSource, TrainingStatus
)

router = APIRouter()


class ModelConfigRequest(BaseModel):
    """Model configuration request"""
    model_id: str = Field(..., min_length=1, max_length=100)
    model_type: str = Field(..., regex=r"^(linear_regression|ridge_regression|lasso_regression|random_forest|gradient_boosting|xgboost|lightgbm|svr)$")
    prediction_target: str = Field(..., regex=r"^(price|return|volatility|direction|trend|support_resistance|volume|sentiment)$")
    features: List[str] = Field(default_factory=list)
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    preprocessing_config: Dict[str, Any] = Field(default_factory=dict)
    training_config: Dict[str, Any] = Field(default_factory=dict)
    evaluation_metrics: List[str] = Field(default_factory=lambda: ['mse', 'mae', 'r2'])
    retrain_frequency: int = Field(30, ge=1, le=365)
    lookback_window: int = Field(252, ge=30, le=1000)
    prediction_horizon: int = Field(5, ge=1, le=30)


class TrainingJobRequest(BaseModel):
    """Training job request"""
    job_id: str = Field(..., min_length=1, max_length=100)
    model_config: ModelConfigRequest
    data_sources: List[str] = Field(..., min_items=1)
    training_period_days: int = Field(365, ge=30, le=1000)
    validation_split: float = Field(0.2, gt=0, lt=1)
    auto_deploy: bool = False
    scheduled_time: Optional[datetime] = None
    priority: int = Field(1, ge=1, le=10)
    symbols: List[str] = Field(default_factory=lambda: ['AAPL'])


class PredictionRequest(BaseModel):
    """Prediction request"""
    model_id: str
    symbols: List[str] = Field(..., min_items=1, max_items=50)
    use_latest_data: bool = True
    custom_data: Optional[Dict[str, Any]] = None


class BatchPredictionRequest(BaseModel):
    """Batch prediction request"""
    model_ids: List[str] = Field(..., min_items=1)
    symbols: List[str] = Field(..., min_items=1, max_items=100)
    ensemble_weights: Optional[List[float]] = None


class EnsembleRequest(BaseModel):
    """Model ensemble request"""
    ensemble_id: str = Field(..., min_length=1, max_length=100)
    model_ids: List[str] = Field(..., min_items=2)
    weights: Optional[List[float]] = None


class AutoRetrainRequest(BaseModel):
    """Auto-retrain request"""
    model_id: str
    retrain_frequency_days: int = Field(30, ge=1, le=365)
    symbols: List[str] = Field(..., min_items=1)


def convert_model_config(config_req: ModelConfigRequest) -> ModelConfig:
    """Convert API request to ModelConfig"""
    from app.services.ml.prediction_models import ModelType, PredictionTarget
    
    return ModelConfig(
        model_id=config_req.model_id,
        model_type=ModelType(config_req.model_type),
        prediction_target=PredictionTarget(config_req.prediction_target),
        features=config_req.features,
        hyperparameters=config_req.hyperparameters,
        preprocessing_config=config_req.preprocessing_config,
        training_config=config_req.training_config,
        evaluation_metrics=config_req.evaluation_metrics,
        retrain_frequency=config_req.retrain_frequency,
        lookback_window=config_req.lookback_window,
        prediction_horizon=config_req.prediction_horizon
    )


async def get_market_data_for_prediction(symbols: List[str]) -> Dict[str, Any]:
    """Get market data for prediction (mock implementation)"""
    import pandas as pd
    import numpy as np
    
    # Mock market data - would integrate with actual data sources
    data = {}
    
    for symbol in symbols:
        # Generate recent market data
        dates = pd.date_range(end=datetime.now(), periods=500, freq='D')
        
        # Simulate realistic price data
        np.random.seed(hash(symbol) % 2**32)
        base_price = 100 + hash(symbol) % 500
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.lognormal(15, 1, len(dates)).astype(int)
        })
        
        data[symbol] = df
    
    return data


@router.post("/models/train", status_code=status.HTTP_202_ACCEPTED)
async def train_model(
    request: TrainingJobRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:train"))
):
    """Train a new ML model"""
    try:
        # Convert request to training job
        model_config = convert_model_config(request.model_config)
        
        # Set custom parameters
        model_config.custom_parameters = {'symbols': request.symbols}
        
        # Convert data sources
        data_sources = []
        for source in request.data_sources:
            try:
                data_sources.append(DataSource(source))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid data source: {source}"
                )
        
        # Create training job
        end_date = datetime.now()
        start_date = end_date - timedelta(days=request.training_period_days)
        
        job = TrainingJob(
            job_id=request.job_id,
            model_config=model_config,
            data_sources=data_sources,
            training_period_start=start_date,
            training_period_end=end_date,
            validation_split=request.validation_split,
            auto_deploy=request.auto_deploy,
            scheduled_time=request.scheduled_time,
            priority=request.priority,
            created_by=str(current_user.id),
            organization_id=str(current_user.organization_id)
        )
        
        # Schedule training
        job_id = await training_pipeline.schedule_training_job(job)
        
        return {
            "message": "Training job scheduled successfully",
            "job_id": job_id,
            "model_id": model_config.model_id,
            "estimated_duration": "10-30 minutes"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/models")
async def list_models(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:read"))
):
    """List all available ML models"""
    try:
        models = ml_prediction_service.list_models()
        return {
            "models": models,
            "total_count": len(models)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/models/{model_id}")
async def get_model_info(
    model_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:read"))
):
    """Get model information"""
    try:
        model_info = ml_prediction_service.get_model_info(model_id)
        
        if not model_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_id} not found"
            )
        
        return model_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/models/{model_id}/predict")
async def make_prediction(
    model_id: str,
    request: PredictionRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:predict"))
):
    """Make predictions using a trained model"""
    try:
        predictions = []
        
        # Get market data for prediction
        if request.use_latest_data:
            market_data = await get_market_data_for_prediction(request.symbols)
        else:
            market_data = request.custom_data or {}
        
        # Make predictions for each symbol
        for symbol in request.symbols:
            if symbol not in market_data:
                continue
                
            prediction = await ml_prediction_service.predict(
                model_id=model_id,
                data=market_data[symbol],
                symbol=symbol
            )
            
            predictions.append({
                'symbol': symbol,
                'predicted_value': prediction.predicted_value,
                'confidence': prediction.confidence,
                'prediction_type': prediction.prediction_type.value,
                'prediction_horizon': prediction.prediction_horizon,
                'timestamp': prediction.prediction_timestamp
            })
        
        return {
            "model_id": model_id,
            "predictions": predictions,
            "prediction_count": len(predictions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/predictions/batch")
async def batch_prediction(
    request: BatchPredictionRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:predict"))
):
    """Make batch predictions using multiple models"""
    try:
        all_predictions = {}
        
        # Get market data
        market_data = await get_market_data_for_prediction(request.symbols)
        
        # Make predictions with each model
        for model_id in request.model_ids:
            model_predictions = []
            
            for symbol in request.symbols:
                if symbol not in market_data:
                    continue
                    
                try:
                    prediction = await ml_prediction_service.predict(
                        model_id=model_id,
                        data=market_data[symbol],
                        symbol=symbol
                    )
                    
                    model_predictions.append({
                        'symbol': symbol,
                        'predicted_value': prediction.predicted_value,
                        'confidence': prediction.confidence
                    })
                except Exception as e:
                    model_predictions.append({
                        'symbol': symbol,
                        'error': str(e)
                    })
            
            all_predictions[model_id] = model_predictions
        
        # Calculate ensemble predictions if weights provided
        ensemble_predictions = []
        if request.ensemble_weights and len(request.ensemble_weights) == len(request.model_ids):
            for symbol in request.symbols:
                weighted_prediction = 0
                total_weight = 0
                
                for i, model_id in enumerate(request.model_ids):
                    model_preds = all_predictions[model_id]
                    symbol_pred = next((p for p in model_preds if p['symbol'] == symbol), None)
                    
                    if symbol_pred and 'predicted_value' in symbol_pred:
                        weight = request.ensemble_weights[i]
                        weighted_prediction += symbol_pred['predicted_value'] * weight
                        total_weight += weight
                
                if total_weight > 0:
                    ensemble_predictions.append({
                        'symbol': symbol,
                        'ensemble_prediction': weighted_prediction / total_weight
                    })
        
        return {
            "individual_predictions": all_predictions,
            "ensemble_predictions": ensemble_predictions,
            "prediction_timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/training-jobs")
async def list_training_jobs(
    status_filter: Optional[str] = Query(None, regex=r"^(pending|running|completed|failed|cancelled)$"),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:read"))
):
    """List training jobs"""
    try:
        status_enum = TrainingStatus(status_filter) if status_filter else None
        jobs = training_pipeline.list_jobs(status_enum)
        
        job_list = []
        for job in jobs:
            job_dict = {
                'job_id': job.job_id,
                'model_id': job.model_id,
                'status': job.status.value,
                'data_points_used': job.data_points_used,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'training_duration': job.training_duration
            }
            
            if job.performance:
                job_dict['performance'] = {
                    'mse': job.performance.mse,
                    'mae': job.performance.mae,
                    'r2_score': job.performance.r2_score,
                    'sharpe_ratio': job.performance.sharpe_ratio,
                    'win_rate': job.performance.win_rate
                }
            
            if job.error_message:
                job_dict['error_message'] = job.error_message
            
            job_list.append(job_dict)
        
        return {
            "jobs": job_list,
            "total_count": len(job_list)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/training-jobs/{job_id}")
async def get_training_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:read"))
):
    """Get training job status"""
    try:
        job_result = training_pipeline.get_job_status(job_id)
        
        if not job_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job {job_id} not found"
            )
        
        result_dict = {
            'job_id': job_result.job_id,
            'model_id': job_result.model_id,
            'status': job_result.status.value,
            'data_points_used': job_result.data_points_used,
            'features_selected': job_result.features_selected,
            'started_at': job_result.started_at,
            'completed_at': job_result.completed_at,
            'training_duration': job_result.training_duration,
            'logs': job_result.logs or []
        }
        
        if job_result.performance:
            result_dict['performance'] = {
                'mse': job_result.performance.mse,
                'mae': job_result.performance.mae,
                'r2_score': job_result.performance.r2_score,
                'sharpe_ratio': job_result.performance.sharpe_ratio,
                'max_drawdown': job_result.performance.max_drawdown,
                'win_rate': job_result.performance.win_rate,
                'profit_factor': job_result.performance.profit_factor
            }
        
        if job_result.error_message:
            result_dict['error_message'] = job_result.error_message
        
        return result_dict
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/training-jobs/{job_id}")
async def cancel_training_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:manage"))
):
    """Cancel a training job"""
    try:
        success = training_pipeline.cancel_job(job_id)
        
        if success:
            return {"message": f"Training job {job_id} cancelled successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job {job_id} not found or cannot be cancelled"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/ensembles", status_code=status.HTTP_201_CREATED)
async def create_model_ensemble(
    request: EnsembleRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:manage"))
):
    """Create a model ensemble"""
    try:
        success = await training_pipeline.create_model_ensemble(
            ensemble_id=request.ensemble_id,
            model_ids=request.model_ids,
            weights=request.weights
        )
        
        if success:
            return {
                "message": f"Model ensemble {request.ensemble_id} created successfully",
                "ensemble_id": request.ensemble_id,
                "model_count": len(request.model_ids)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create model ensemble"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/models/{model_id}/auto-retrain")
async def schedule_auto_retrain(
    model_id: str,
    request: AutoRetrainRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:manage"))
):
    """Schedule automatic model retraining"""
    try:
        job_id = await training_pipeline.schedule_auto_retrain(
            model_id=model_id,
            retrain_frequency_days=request.retrain_frequency_days,
            symbols=request.symbols
        )
        
        return {
            "message": f"Auto-retrain scheduled for model {model_id}",
            "retrain_job_id": job_id,
            "frequency_days": request.retrain_frequency_days
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/model-types")
async def get_model_types(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:read"))
):
    """Get available model types"""
    model_types = {
        "linear_regression": {
            "name": "Linear Regression",
            "description": "Simple linear relationship between features and target",
            "use_cases": ["Basic trend prediction", "Baseline model"],
            "complexity": "Low"
        },
        "ridge_regression": {
            "name": "Ridge Regression", 
            "description": "Linear regression with L2 regularization",
            "use_cases": ["Feature selection", "Overfitting prevention"],
            "complexity": "Low"
        },
        "random_forest": {
            "name": "Random Forest",
            "description": "Ensemble of decision trees",
            "use_cases": ["General purpose", "Feature importance", "Non-linear patterns"],
            "complexity": "Medium"
        },
        "xgboost": {
            "name": "XGBoost",
            "description": "Gradient boosting framework",
            "use_cases": ["High accuracy", "Competition-grade performance"],
            "complexity": "High"
        },
        "lightgbm": {
            "name": "LightGBM",
            "description": "Fast gradient boosting framework",
            "use_cases": ["Large datasets", "Fast training"],
            "complexity": "High"
        }
    }
    
    return {"model_types": model_types}


@router.get("/prediction-targets")
async def get_prediction_targets(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:read"))
):
    """Get available prediction targets"""
    targets = {
        "price": "Future price prediction",
        "return": "Future return prediction", 
        "volatility": "Volatility forecasting",
        "direction": "Price direction (up/down)",
        "trend": "Market trend identification",
        "support_resistance": "Support/resistance levels",
        "volume": "Volume prediction",
        "sentiment": "Market sentiment prediction"
    }
    
    return {"prediction_targets": targets}


@router.get("/data-sources")
async def get_data_sources(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("ml:read"))
):
    """Get available data sources for training"""
    sources = {
        "market_data": {
            "name": "Market Data",
            "description": "OHLCV price and volume data",
            "required": True
        },
        "fundamental_data": {
            "name": "Fundamental Data", 
            "description": "Financial statements and ratios",
            "required": False
        },
        "news_sentiment": {
            "name": "News Sentiment",
            "description": "Sentiment analysis from financial news",
            "required": False
        },
        "social_sentiment": {
            "name": "Social Sentiment",
            "description": "Social media sentiment analysis", 
            "required": False
        },
        "economic_indicators": {
            "name": "Economic Indicators",
            "description": "Macroeconomic data",
            "required": False
        },
        "options_data": {
            "name": "Options Data",
            "description": "Options flow and volatility data",
            "required": False
        }
    }
    
    return {"data_sources": sources}