from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv
import logging
from api.routes import auth, users, subscriptions, brokers, trading, predictions, market, portfolio, strategies, backtesting, watchlists, websocket, auto_trading, reports
from services.database import init_db, close_db
from services.auth_service import verify_token
from services.auto_trading_service import auto_trading_service
from utils.middleware import add_cors_headers, add_security_headers, rate_limit_middleware
from utils.logging_config import setup_logging
from websocket.broadcast_service import broadcast_service

load_dotenv()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# FastAPI lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI Trading Platform API")
    await init_db()
    await broadcast_service.start()
    await auto_trading_service.start_service()
    yield
    # Shutdown
    logger.info("Shutting down AI Trading Platform API")
    await auto_trading_service.stop_service()
    await broadcast_service.stop()
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="AI Trading Platform API",
    description="AI-powered trading platform with automated trading, ML predictions, and real-time market data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Security
security = HTTPBearer()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
)

# Custom middleware
app.middleware("http")(add_cors_headers)
app.middleware("http")(add_security_headers)
app.middleware("http")(rate_limit_middleware)

# Health check endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "trading-platform-api"}

@app.get("/ready")
async def readiness_check():
    return {"status": "ready", "service": "trading-platform-api"}

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = verify_token(token)
        return payload
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Include API routes
app.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/v1/users", tags=["Users"], dependencies=[Depends(get_current_user)])
app.include_router(subscriptions.router, prefix="/v1/subscriptions", tags=["Subscriptions"])
app.include_router(brokers.router, prefix="/v1/brokers", tags=["Brokers"], dependencies=[Depends(get_current_user)])
app.include_router(trading.router, prefix="/v1/trading", tags=["Trading"], dependencies=[Depends(get_current_user)])
app.include_router(predictions.router, prefix="/v1/predictions", tags=["AI Predictions"], dependencies=[Depends(get_current_user)])
app.include_router(market.router, prefix="/v1/market", tags=["Market Data"], dependencies=[Depends(get_current_user)])
app.include_router(portfolio.router, prefix="/v1/portfolio", tags=["Portfolio"], dependencies=[Depends(get_current_user)])
app.include_router(strategies.router, prefix="/v1/strategies", tags=["Strategies"], dependencies=[Depends(get_current_user)])
app.include_router(backtesting.router, prefix="/v1/backtesting", tags=["Backtesting"], dependencies=[Depends(get_current_user)])
app.include_router(watchlists.router, prefix="/v1/watchlists", tags=["Watchlists"], dependencies=[Depends(get_current_user)])
app.include_router(auto_trading.router, prefix="/v1/auto-trading", tags=["Auto Trading"], dependencies=[Depends(get_current_user)])
app.include_router(reports.router, prefix="/v1/reports", tags=["Reports"], dependencies=[Depends(get_current_user)])
app.include_router(websocket.router, prefix="/v1/ws", tags=["WebSocket"])

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )