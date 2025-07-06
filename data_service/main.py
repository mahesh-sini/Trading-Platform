from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
import logging
from api.routes import market_data, news, real_time
from services.data_ingestion import data_ingestion_service
from services.market_data_service import market_data_service
from utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Data Service")
    await data_ingestion_service.initialize()
    await market_data_service.initialize()
    yield
    # Shutdown
    logger.info("Shutting down Data Service")
    await data_ingestion_service.shutdown()

# Create FastAPI app
app = FastAPI(
    title="AI Trading Platform - Data Service",
    description="Market data ingestion and real-time data feeds service",
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
    return {"status": "healthy", "service": "data-service"}

@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "data-service"}

# Include API routes
app.include_router(market_data.router, prefix="/v1/market-data", tags=["Market Data"])
app.include_router(news.router, prefix="/v1/news", tags=["News"])
app.include_router(real_time.router, prefix="/v1/real-time", tags=["Real Time"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("DATA_SERVICE_PORT", 8002)),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )