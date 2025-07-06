import httpx
import logging
from typing import Dict, Optional, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class MLServiceClient:
    """Client for communicating with the ML service"""
    
    def __init__(self):
        self.base_url = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
        self.timeout = httpx.Timeout(30.0)
        
    async def get_prediction(self, symbol: str, timeframe: str = "intraday") -> Optional[Dict[str, Any]]:
        """Get ML prediction for a symbol"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/predict",
                    json={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "predicted_price": data.get("predicted_price"),
                        "confidence": data.get("confidence", 0.0),
                        "prediction_interval": data.get("prediction_interval", []),
                        "features_used": data.get("features_used", []),
                        "model_version": data.get("model_version", "unknown"),
                        "timestamp": data.get("timestamp")
                    }
                else:
                    logger.warning(f"ML service returned status {response.status_code} for {symbol}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout getting ML prediction for {symbol}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error getting ML prediction for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting ML prediction for {symbol}: {e}")
            return None
    
    async def get_multiple_predictions(self, symbols: list, timeframe: str = "intraday") -> Dict[str, Optional[Dict[str, Any]]]:
        """Get ML predictions for multiple symbols"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/predict/batch",
                    json={
                        "symbols": symbols,
                        "timeframe": timeframe,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"ML service returned status {response.status_code} for batch prediction")
                    return {symbol: None for symbol in symbols}
                    
        except Exception as e:
            logger.error(f"Error getting batch ML predictions: {e}")
            return {symbol: None for symbol in symbols}
    
    async def get_model_performance(self, symbol: str, model_name: str = None) -> Optional[Dict[str, Any]]:
        """Get model performance metrics"""
        try:
            params = {"symbol": symbol}
            if model_name:
                params["model_name"] = model_name
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/models/performance",
                    params=params
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"ML service returned status {response.status_code} for model performance")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting model performance: {e}")
            return None
    
    async def retrain_model(self, symbol: str, force: bool = False) -> bool:
        """Trigger model retraining"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:  # 5 min timeout for training
                response = await client.post(
                    f"{self.base_url}/models/retrain",
                    json={
                        "symbol": symbol,
                        "force": force,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error triggering model retraining for {symbol}: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if ML service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

# Global ML service client instance
ml_service_client = MLServiceClient()