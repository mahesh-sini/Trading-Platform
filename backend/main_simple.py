from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Trading Platform API",
    description="RESTful API for AI-powered trading platform",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import only working routes
try:
    from api.routes import auth
    app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
    logger.info("✅ Auth routes loaded")
except Exception as e:
    logger.warning(f"⚠️ Could not load auth routes: {e}")

try:
    from api.routes import market
    app.include_router(market.router, prefix="/api/market", tags=["market"])
    logger.info("✅ Market routes loaded")
except Exception as e:
    logger.warning(f"⚠️ Could not load market routes: {e}")

try:
    from api.routes import subscriptions
    app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
    logger.info("✅ Subscription routes loaded")
except Exception as e:
    logger.warning(f"⚠️ Could not load subscription routes: {e}")

@app.get("/")
async def root():
    return {"message": "AI Trading Platform API", "status": "running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "trading-api"}

@app.get("/api/status")
async def api_status():
    return {
        "status": "running",
        "service": "AI Trading Platform Backend",
        "version": "1.0.0",
        "database": "SQLite (local testing)",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting AI Trading Platform Backend on port {port}")
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )