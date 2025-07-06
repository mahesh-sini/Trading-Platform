"""
Live Market Data API Routes - Production Implementation
Replaces mock data with real Indian market data providers
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import asyncio
import json
import logging
from datetime import datetime, timedelta

from services.live_market_data import live_market_data_service
from models.market_data import Quote, HistoricalBar
from services.auth import get_current_user
from services.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/market", tags=["live-market"])

@router.on_event("startup")
async def startup_market_service():
    """Initialize live market data service on startup"""
    try:
        await live_market_data_service.initialize()
        logger.info("Live market data service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize market data service: {e}")

@router.on_event("shutdown")
async def shutdown_market_service():
    """Clean up market data service on shutdown"""
    try:
        await live_market_data_service.close()
        logger.info("Live market data service shut down")
    except Exception as e:
        logger.error(f"Error shutting down market data service: {e}")

@router.get("/quote/{symbol}")
async def get_live_quote(
    symbol: str,
    exchange: str = Query("NSE", description="Exchange (NSE, BSE)"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get real-time quote for a symbol
    
    Replaces: Mock data in dashboard components
    Provides: Live market data from NSE, Yahoo Finance, Alpha Vantage
    """
    try:
        quote = await live_market_data_service.get_live_quote(symbol, exchange)
        
        if not quote:
            raise HTTPException(
                status_code=404,
                detail=f"No live quote data found for symbol {symbol}"
            )
        
        # Add metadata for client
        quote.update({
            "request_time": datetime.now().isoformat(),
            "data_source": "live_market_api",
            "user_id": current_user["user_id"]
        })
        
        return {
            "success": True,
            "data": quote,
            "message": f"Live quote for {symbol}"
        }
        
    except Exception as e:
        logger.error(f"Error fetching live quote for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch live quote for {symbol}: {str(e)}"
        )

@router.get("/quotes/batch")
async def get_batch_quotes(
    symbols: List[str] = Query(..., description="List of symbols to fetch"),
    exchange: str = Query("NSE", description="Exchange (NSE, BSE)"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get live quotes for multiple symbols (batch request)
    
    Optimized for dashboard watchlist updates
    """
    try:
        if len(symbols) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 symbols allowed per batch request"
            )
        
        # Fetch quotes concurrently
        tasks = [
            live_market_data_service.get_live_quote(symbol, exchange)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        quotes = {}
        errors = []
        
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                errors.append(f"Error fetching {symbol}: {str(result)}")
            elif result:
                quotes[symbol] = result
            else:
                errors.append(f"No data found for {symbol}")
        
        return {
            "success": True,
            "data": {
                "quotes": quotes,
                "symbols_requested": symbols,
                "symbols_found": list(quotes.keys()),
                "errors": errors
            },
            "message": f"Batch quotes for {len(quotes)}/{len(symbols)} symbols"
        }
        
    except Exception as e:
        logger.error(f"Error in batch quotes request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch batch quotes: {str(e)}"
        )

@router.get("/indices")
async def get_indian_indices(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get live Indian market indices (NIFTY, SENSEX, BANKNIFTY)
    
    Replaces: Mock indices data in dashboard
    """
    try:
        indices_symbols = ["^NSEI", "^BSESN", "^NSEBANK"]  # Yahoo Finance symbols
        index_names = ["NIFTY", "SENSEX", "BANKNIFTY"]
        
        tasks = [
            live_market_data_service.get_live_quote(symbol, "NSE")
            for symbol in indices_symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        indices = []
        for name, symbol, result in zip(index_names, indices_symbols, results):
            if isinstance(result, Exception) or not result:
                # Fallback to last known values if live data unavailable
                fallback_data = {
                    "NIFTY": {"price": 19674.25, "change": 156.80, "changePercent": 0.80},
                    "SENSEX": {"price": 65930.77, "change": 442.65, "changePercent": 0.68},
                    "BANKNIFTY": {"price": 43567.90, "change": -234.50, "changePercent": -0.53}
                }
                data = fallback_data.get(name, {"price": 0, "change": 0, "changePercent": 0})
                indices.append({
                    "symbol": name,
                    "price": data["price"],
                    "change": data["change"],
                    "changePercent": data["changePercent"],
                    "data_source": "fallback"
                })
            else:
                indices.append({
                    "symbol": name,
                    "price": result.get("price", 0),
                    "change": result.get("change", 0),
                    "changePercent": result.get("change_percent", 0),
                    "volume": result.get("volume", 0),
                    "data_source": "live"
                })
        
        return {
            "success": True,
            "data": indices,
            "message": "Indian market indices data"
        }
        
    except Exception as e:
        logger.error(f"Error fetching indices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch indices: {str(e)}"
        )

@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = Query("1d", description="Period (1d, 5d, 1m, 3m, 6m, 1y)"),
    interval: str = Query("1d", description="Interval (1m, 5m, 15m, 1h, 1d)"),
    exchange: str = Query("NSE", description="Exchange"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get historical market data for charting
    
    Replaces: Mock chart data in TradingChart component
    """
    try:
        # Convert period to date range
        period_map = {
            "1d": 1, "5d": 5, "1m": 30, "3m": 90, "6m": 180, "1y": 365
        }
        
        if period not in period_map:
            raise HTTPException(status_code=400, detail="Invalid period")
        
        days = period_map[period]
        start_date = datetime.now() - timedelta(days=days)
        end_date = datetime.now()
        
        historical_data = await live_market_data_service.get_historical_data(
            symbol=symbol,
            period=interval,
            start_date=start_date,
            end_date=end_date
        )
        
        if not historical_data:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for {symbol}"
            )
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "bars": historical_data,
                "total_bars": len(historical_data)
            },
            "message": f"Historical data for {symbol}"
        }
        
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch historical data: {str(e)}"
        )

@router.post("/subscribe")
async def subscribe_to_real_time(
    symbols: List[str],
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Subscribe to real-time updates for symbols
    
    Sets up WebSocket streaming for dashboard
    """
    try:
        if len(symbols) > 20:
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 symbols allowed for real-time subscription"
            )
        
        await live_market_data_service.subscribe_to_real_time(symbols)
        
        return {
            "success": True,
            "data": {
                "subscribed_symbols": symbols,
                "subscription_time": datetime.now().isoformat()
            },
            "message": f"Subscribed to real-time updates for {len(symbols)} symbols"
        }
        
    except Exception as e:
        logger.error(f"Error subscribing to real-time updates: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to subscribe to real-time updates: {str(e)}"
        )

@router.get("/market-movers")
async def get_market_movers(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get top gainers and losers for the day
    
    Replaces: Mock market movers data in dashboard
    """
    try:
        # Popular Indian stocks for market movers analysis
        stocks = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "KOTAKBANK",
            "LT", "ITC", "WIPRO", "MARUTI", "BHARTIARTL", "ASIANPAINT",
            "ADANIGREEN", "TATAMOTORS", "BAJFINANCE", "ZEEL", "YESBANK", "SUZLON"
        ]
        
        # Fetch quotes for analysis
        tasks = [
            live_market_data_service.get_live_quote(symbol, "NSE")
            for symbol in stocks
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_stocks = []
        for symbol, result in zip(stocks, results):
            if not isinstance(result, Exception) and result:
                valid_stocks.append({
                    "symbol": symbol,
                    "price": result.get("price", 0),
                    "change": result.get("change", 0),
                    "changePercent": result.get("change_percent", 0)
                })
        
        # Sort by change percentage
        valid_stocks.sort(key=lambda x: x["changePercent"], reverse=True)
        
        top_gainers = valid_stocks[:5]
        top_losers = valid_stocks[-5:]
        
        return {
            "success": True,
            "data": {
                "top_gainers": top_gainers,
                "top_losers": top_losers,
                "analysis_time": datetime.now().isoformat()
            },
            "message": "Market movers data"
        }
        
    except Exception as e:
        logger.error(f"Error fetching market movers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market movers: {str(e)}"
        )

@router.get("/stream/{symbol}")
async def stream_real_time_data(
    symbol: str,
    exchange: str = Query("NSE"),
    current_user: dict = Depends(get_current_user)
):
    """
    Stream real-time data for a symbol using Server-Sent Events
    
    Alternative to WebSocket for real-time dashboard updates
    """
    async def generate_stream():
        try:
            while True:
                quote = await live_market_data_service.get_live_quote(symbol, exchange)
                if quote:
                    data = {
                        "type": "quote_update",
                        "symbol": symbol,
                        "data": quote,
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                
                await asyncio.sleep(2)  # Update every 2 seconds
                
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for {symbol}")
        except Exception as e:
            logger.error(f"Error in stream for {symbol}: {e}")
            error_data = {
                "type": "error",
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@router.get("/health")
async def market_data_health():
    """
    Health check for market data service
    """
    try:
        # Test a simple quote fetch
        test_quote = await live_market_data_service.get_live_quote("RELIANCE", "NSE")
        
        return {
            "success": True,
            "data": {
                "service_status": "healthy",
                "providers_available": [
                    provider for provider, config in live_market_data_service.providers.items()
                    if config.get("enabled", False)
                ],
                "test_quote_available": bool(test_quote),
                "check_time": datetime.now().isoformat()
            },
            "message": "Market data service is healthy"
        }
        
    except Exception as e:
        logger.error(f"Market data health check failed: {e}")
        return {
            "success": False,
            "data": {
                "service_status": "unhealthy",
                "error": str(e),
                "check_time": datetime.now().isoformat()
            },
            "message": "Market data service health check failed"
        }