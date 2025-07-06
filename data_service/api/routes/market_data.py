from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from services.market_data_service import market_data_service
from services.data_ingestion import data_ingestion_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class QuoteResponse(BaseModel):
    symbol: str
    price: float
    bid: float
    ask: float
    volume: int
    change: float
    change_percent: float
    market_status: str
    timestamp: str

class SymbolSearchRequest(BaseModel):
    query: str
    limit: int = 10
    
    @validator('query')
    def validate_query(cls, v):
        if len(v.strip()) < 1:
            raise ValueError('Query cannot be empty')
        return v.strip()

class SymbolInfoResponse(BaseModel):
    symbol: str
    company_name: str
    exchange: str
    sector: str
    industry: str
    market_cap: float
    shares_outstanding: float

@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str, force_refresh: bool = False):
    """Get current quote for a symbol"""
    try:
        symbol = symbol.upper()
        quote = await market_data_service.get_quote(symbol, force_refresh)
        
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quote not found for symbol: {symbol}"
            )
        
        return QuoteResponse(
            symbol=quote.symbol,
            price=quote.price,
            bid=quote.bid,
            ask=quote.ask,
            volume=quote.volume,
            change=quote.change,
            change_percent=quote.change_percent,
            market_status=quote.market_status.value,
            timestamp=quote.timestamp.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get quote for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quote"
        )

@router.post("/quotes/batch")
async def get_quotes_batch(symbols: List[str]):
    """Get quotes for multiple symbols"""
    try:
        if len(symbols) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 symbols allowed per request"
            )
        
        symbols = [symbol.upper() for symbol in symbols]
        quotes = await market_data_service.get_quotes_batch(symbols)
        
        response = {}
        for symbol, quote in quotes.items():
            response[symbol] = QuoteResponse(
                symbol=quote.symbol,
                price=quote.price,
                bid=quote.bid,
                ask=quote.ask,
                volume=quote.volume,
                change=quote.change,
                change_percent=quote.change_percent,
                market_status=quote.market_status.value,
                timestamp=quote.timestamp.isoformat()
            )
        
        return {"quotes": response, "total": len(response)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch quotes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch quotes"
        )

@router.get("/history/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = Query("1y", regex="^(1d|5d|1mo|3mo|6mo|1y|2y|5y|10y|ytd|max)$"),
    interval: str = Query("1d", regex="^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$")
):
    """Get historical market data for a symbol"""
    try:
        symbol = symbol.upper()
        data = await market_data_service.get_historical_data(symbol, period, interval)
        
        if data.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No historical data found for symbol: {symbol}"
            )
        
        # Convert DataFrame to list of dictionaries
        data_records = data.to_dict('records')
        
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data": data_records,
            "count": len(data_records)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get historical data for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve historical data"
        )

@router.get("/info/{symbol}", response_model=SymbolInfoResponse)
async def get_symbol_info(symbol: str):
    """Get detailed information about a symbol"""
    try:
        symbol = symbol.upper()
        info = await market_data_service.get_symbol_info(symbol)
        
        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Symbol information not found: {symbol}"
            )
        
        return SymbolInfoResponse(
            symbol=info.symbol,
            company_name=info.company_name,
            exchange=info.exchange,
            sector=info.sector,
            industry=info.industry,
            market_cap=info.market_cap,
            shares_outstanding=info.shares_outstanding
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get symbol info for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve symbol information"
        )

@router.post("/search")
async def search_symbols(request: SymbolSearchRequest):
    """Search for symbols by name or ticker"""
    try:
        results = await market_data_service.search_symbols(request.query, request.limit)
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Symbol search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Symbol search failed"
        )

@router.get("/market-hours")
async def get_market_hours(exchange: str = "NYSE"):
    """Get market hours for an exchange"""
    try:
        hours = await market_data_service.get_market_hours(exchange)
        return hours
        
    except Exception as e:
        logger.error(f"Failed to get market hours: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market hours"
        )

@router.post("/subscribe/{symbol}")
async def subscribe_to_symbol(symbol: str, background_tasks: BackgroundTasks):
    """Subscribe to real-time updates for a symbol"""
    try:
        symbol = symbol.upper()
        await market_data_service.subscribe_to_symbol(symbol)
        
        return {
            "message": f"Subscribed to {symbol}",
            "symbol": symbol,
            "status": "subscribed"
        }
        
    except Exception as e:
        logger.error(f"Failed to subscribe to {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to symbol"
        )

@router.delete("/subscribe/{symbol}")
async def unsubscribe_from_symbol(symbol: str):
    """Unsubscribe from real-time updates for a symbol"""
    try:
        symbol = symbol.upper()
        await market_data_service.unsubscribe_from_symbol(symbol)
        
        return {
            "message": f"Unsubscribed from {symbol}",
            "symbol": symbol,
            "status": "unsubscribed"
        }
        
    except Exception as e:
        logger.error(f"Failed to unsubscribe from {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from symbol"
        )

@router.get("/status")
async def get_service_status():
    """Get market data service status"""
    try:
        subscriptions_count = len(market_data_service.subscriptions)
        websocket_connections = len(market_data_service.websocket_connections)
        
        return {
            "status": "healthy",
            "service": "market-data",
            "subscriptions": subscriptions_count,
            "websocket_connections": websocket_connections,
            "cache_available": market_data_service.redis_client is not None,
            "data_sources": ["yahoo_finance", "alpha_vantage"]
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Status check failed"
        )