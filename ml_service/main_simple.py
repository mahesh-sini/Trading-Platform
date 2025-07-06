from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Trading Platform - ML Service",
    description="Machine Learning service for stock price predictions and market analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ml-service"}

@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "ml-service"}

@app.get("/")
async def root():
    return {"message": "AI Trading Platform ML Service", "status": "running", "version": "1.0.0"}

# Mock ML prediction endpoints
@app.post("/v1/predictions/price")
async def predict_price(request: Dict = None):
    """Predict stock price for given symbol"""
    import random
    
    symbol = request.get("symbol", "AAPL") if request else "AAPL"
    horizon = request.get("horizon", "1d") if request else "1d"
    
    # Mock prediction
    current_price = 150 + random.uniform(-50, 50)
    predicted_change = random.uniform(-0.05, 0.05)  # -5% to +5%
    predicted_price = current_price * (1 + predicted_change)
    
    return {
        "symbol": symbol,
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "predicted_change": round(predicted_change * 100, 2),
        "confidence": round(random.uniform(0.6, 0.9), 2),
        "horizon": horizon,
        "timestamp": datetime.now().isoformat(),
        "model": "mock_lstm_v1.0"
    }

@app.post("/v1/predictions/direction")
async def predict_direction(request: Dict = None):
    """Predict price direction (up/down) for given symbol"""
    import random
    
    symbol = request.get("symbol", "AAPL") if request else "AAPL"
    
    directions = ["up", "down", "neutral"]
    direction = random.choice(directions)
    confidence = random.uniform(0.5, 0.9)
    
    return {
        "symbol": symbol,
        "predicted_direction": direction,
        "confidence": round(confidence, 2),
        "probability": {
            "up": round(random.uniform(0.2, 0.8), 2),
            "down": round(random.uniform(0.2, 0.8), 2),
            "neutral": round(random.uniform(0.1, 0.3), 2)
        },
        "timestamp": datetime.now().isoformat(),
        "model": "mock_classifier_v1.0"
    }

@app.get("/v1/models/status")
async def model_status():
    """Get status of ML models"""
    return {
        "models": {
            "price_predictor": {
                "status": "loaded",
                "version": "1.0",
                "accuracy": 0.85,
                "last_trained": "2025-01-01T00:00:00Z"
            },
            "direction_classifier": {
                "status": "loaded", 
                "version": "1.0",
                "accuracy": 0.78,
                "last_trained": "2025-01-01T00:00:00Z"
            },
            "sentiment_analyzer": {
                "status": "loaded",
                "version": "1.0", 
                "accuracy": 0.82,
                "last_trained": "2025-01-01T00:00:00Z"
            }
        },
        "system": {
            "gpu_available": False,
            "memory_usage": "45%",
            "cpu_usage": "23%"
        }
    }

@app.get("/v1/features/technical/{symbol}")
async def get_technical_features(symbol: str):
    """Get technical analysis features for a symbol"""
    import random
    
    return {
        "symbol": symbol,
        "features": {
            "rsi": round(random.uniform(20, 80), 2),
            "macd": round(random.uniform(-2, 2), 3),
            "bollinger_upper": round(150 + random.uniform(0, 20), 2),
            "bollinger_lower": round(150 - random.uniform(0, 20), 2),
            "sma_20": round(150 + random.uniform(-10, 10), 2),
            "sma_50": round(150 + random.uniform(-15, 15), 2),
            "volume_sma": random.randint(1000000, 5000000),
            "volatility": round(random.uniform(0.15, 0.45), 3)
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("ML_SERVICE_PORT", 8004))
    logger.info(f"🚀 Starting ML Service on port {port}")
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )