from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from services.feature_engineering import feature_service, FeatureType
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class FeatureExtractionRequest(BaseModel):
    symbol: str
    data_points: int = 100
    feature_types: List[str] = ["technical"]
    custom_features: Optional[List[str]] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()
    
    @validator('feature_types')
    def validate_feature_types(cls, v):
        valid_types = ['technical', 'fundamental', 'sentiment', 'macro', 'alternative']
        for feature_type in v:
            if feature_type not in valid_types:
                raise ValueError(f'Feature type must be one of: {valid_types}')
        return v

class FeatureInfo(BaseModel):
    name: str
    type: str
    description: str
    dependencies: List[str]
    is_available: bool

@router.get("/available", response_model=List[FeatureInfo])
async def get_available_features(feature_type: Optional[str] = None):
    """Get list of available features"""
    try:
        features_info = []
        
        for feature_name, feature_def in feature_service.feature_definitions.items():
            # Apply filter if specified
            if feature_type and feature_def.feature_type.value != feature_type:
                continue
            
            features_info.append(FeatureInfo(
                name=feature_def.name,
                type=feature_def.feature_type.value,
                description=feature_def.description,
                dependencies=feature_def.dependencies,
                is_available=await feature_service.is_feature_available(feature_def.name)
            ))
        
        return features_info
        
    except Exception as e:
        logger.error(f"Failed to get available features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available features"
        )

@router.post("/extract")
async def extract_features(request: FeatureExtractionRequest):
    """Extract features for a symbol"""
    try:
        # Get real market data from data service
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                # Request historical data for feature extraction
                response = await client.get(
                    f"http://localhost:8002/v1/market-data/{request.symbol}/history",
                    params={
                        "period": f"{request.data_points}d",
                        "interval": "1d"
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to get market data: {response.status_code}"
                    )
                
                history_data = response.json()
                if not history_data.get('data'):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"No market data available for {request.symbol}"
                    )
                
                market_data = pd.DataFrame(history_data['data'])
                
                # Ensure required columns exist
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in market_data.columns]
                if missing_columns:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Missing required columns: {missing_columns}"
                    )
                
                if len(market_data) < 20:  # Need minimum data for technical indicators
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Insufficient data for feature extraction. Got {len(market_data)} records, need at least 20"
                    )
                
                logger.info(f"Retrieved {len(market_data)} records for feature extraction: {request.symbol}")
                
            except httpx.RequestError as e:
                logger.error(f"Failed to connect to data service: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Data service unavailable"
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to get market data: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve market data"
                )
        
        # Determine which features to extract
        if request.custom_features:
            feature_list = request.custom_features
        else:
            # Get features based on requested types
            feature_list = []
            for feature_name, feature_def in feature_service.feature_definitions.items():
                if feature_def.feature_type.value in request.feature_types:
                    feature_list.append(feature_name)
        
        # Extract features
        features_df = await feature_service.extract_features(
            data=market_data,
            feature_list=feature_list,
            symbol=request.symbol
        )
        
        # Convert to response format
        features_data = {}
        for feature_name in feature_list:
            if feature_name in features_df.columns:
                feature_values = features_df[feature_name].dropna()
                features_data[feature_name] = {
                    'values': feature_values.tolist()[-10:],  # Last 10 values
                    'current_value': float(feature_values.iloc[-1]) if len(feature_values) > 0 else None,
                    'mean': float(feature_values.mean()) if len(feature_values) > 0 else None,
                    'std': float(feature_values.std()) if len(feature_values) > 0 else None
                }
        
        return {
            "symbol": request.symbol,
            "feature_count": len(features_data),
            "data_points": len(market_data),
            "features": features_data,
            "extraction_timestamp": pd.Timestamp.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Feature extraction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Feature extraction failed"
        )

@router.get("/importance/{symbol}")
async def get_feature_importance(
    symbol: str,
    model_type: Optional[str] = None,
    timeframe: Optional[str] = None
):
    """Get feature importance for a symbol"""
    try:
        # Get actual feature importance from trained models
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                # Get model list for this symbol
                models_response = await client.get(
                    f"http://localhost:8001/v1/models/list",
                    params={"symbol": symbol, "timeframe": timeframe} if timeframe else {"symbol": symbol},
                    timeout=10.0
                )
                
                if models_response.status_code == 200:
                    models_data = models_response.json()
                    if models_data:
                        # Use the best performing model's feature importance
                        best_model = max(models_data, key=lambda x: x.get('performance_metrics', {}).get('directional_accuracy', 0))
                        feature_importance = best_model.get('feature_importance', {})
                        
                        if feature_importance:
                            sample_importance = feature_importance
                        else:
                            # Fallback if no feature importance available
                            sample_importance = await feature_service.calculate_feature_importance(symbol)
                    else:
                        sample_importance = await feature_service.calculate_feature_importance(symbol)
                else:
                    # Fallback if models service unavailable
                    sample_importance = await feature_service.calculate_feature_importance(symbol)
                    
            except Exception as e:
                logger.warning(f"Failed to get model feature importance: {e}")
                # Fallback to feature service calculation
                sample_importance = await feature_service.calculate_feature_importance(symbol)
        
        return {
            "symbol": symbol.upper(),
            "model_type": model_type,
            "timeframe": timeframe,
            "feature_importance": sample_importance,
            "top_features": sorted(sample_importance.items(), key=lambda x: x[1], reverse=True)[:5]
        }
        
    except Exception as e:
        logger.error(f"Failed to get feature importance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feature importance"
        )

@router.get("/correlation")
async def get_feature_correlation(
    features: List[str],
    symbol: Optional[str] = None,
    days: int = 100
):
    """Get correlation matrix for specified features"""
    try:
        if len(features) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 features required for correlation analysis"
            )
        
        # Get real market data for correlation analysis
        import httpx
        async with httpx.AsyncClient() as client:
            try:
                # Get historical data
                response = await client.get(
                    f"http://localhost:8002/v1/market-data/{symbol}/history" if symbol else "http://localhost:8002/v1/market-data/SPY/history",
                    params={"period": f"{days}d", "interval": "1d"},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Failed to get market data for correlation analysis"
                    )
                
                history_data = response.json()
                market_data = pd.DataFrame(history_data['data'])
                
                # Extract the requested features
                features_df = await feature_service.extract_features(
                    data=market_data,
                    feature_list=features,
                    symbol=symbol or "SPY"
                )
                
                # Calculate correlation matrix
                correlation_matrix = features_df[features].corr()
                
            except Exception as e:
                logger.error(f"Failed to get real data for correlation: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to calculate feature correlation"
                )
        
        return {
            "features": features,
            "symbol": symbol,
            "correlation_matrix": correlation_matrix.to_dict(),
            "analysis_period_days": days,
            "high_correlations": [
                {"feature_1": feat1, "feature_2": feat2, "correlation": float(corr)}
                for feat1 in features
                for feat2 in features
                if feat1 != feat2 and abs(correlation_matrix.loc[feat1, feat2]) > 0.7
            ]
        }
        
    except Exception as e:
        logger.error(f"Correlation analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Correlation analysis failed"
        )

@router.get("/sentiment/{symbol}")
async def get_sentiment_features(symbol: str):
    """Get sentiment-based features for a symbol"""
    try:
        sentiment_features = await feature_service.get_sentiment_features(symbol)
        
        return {
            "symbol": symbol.upper(),
            "sentiment_features": sentiment_features,
            "last_updated": pd.Timestamp.now().isoformat(),
            "data_sources": ["news_apis", "social_media", "analyst_reports"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get sentiment features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sentiment features"
        )

@router.get("/fundamental/{symbol}")
async def get_fundamental_features(symbol: str):
    """Get fundamental analysis features for a symbol"""
    try:
        fundamental_features = await feature_service.get_fundamental_features(symbol)
        
        return {
            "symbol": symbol.upper(),
            "fundamental_features": fundamental_features,
            "last_updated": pd.Timestamp.now().isoformat(),
            "data_sources": ["financial_statements", "sec_filings", "earnings_reports"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get fundamental features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get fundamental features"
        )

@router.get("/macro")
async def get_macro_features():
    """Get macroeconomic features"""
    try:
        macro_features = await feature_service.get_macro_features()
        
        return {
            "macro_features": macro_features,
            "last_updated": pd.Timestamp.now().isoformat(),
            "data_sources": ["federal_reserve", "bureau_of_labor", "commerce_department"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get macro features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get macro features"
        )