from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
import logging
from api.routes import predictions, models, features, deployment
from services.ml_engine import ml_engine
from services.feature_engineering import feature_service
from services.model_deployment import model_deployment_service
from utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ML Service")
    await ml_engine.initialize()
    await feature_service.initialize()
    await model_deployment_service.initialize()
    yield
    # Shutdown
    logger.info("Shutting down ML Service")
    await ml_engine.shutdown()
    await model_deployment_service.cleanup()

# Create FastAPI app
app = FastAPI(
    title="AI Trading Platform - ML Service",
    description="Machine Learning service for stock price predictions and market analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
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

# Include API routes
app.include_router(predictions.router, prefix="/v1/predictions", tags=["Predictions"])
app.include_router(models.router, prefix="/v1/models", tags=["Models"])
app.include_router(features.router, prefix="/v1/features", tags=["Features"])
app.include_router(deployment.router, prefix="/v1/deployment", tags=["Deployment"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("ML_SERVICE_PORT", 8001)),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )