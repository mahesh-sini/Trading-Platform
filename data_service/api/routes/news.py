from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, validator
from typing import List, Optional
from services.data_ingestion import data_ingestion_service, DataSource
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class NewsResponse(BaseModel):
    headline: str
    summary: str
    url: str
    source: str
    published_at: str
    symbols: List[str]
    sentiment_score: Optional[float] = None

class NewsSearchRequest(BaseModel):
    symbol: Optional[str] = None
    limit: int = 50
    data_source: Optional[str] = None
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v

@router.get("/latest")
async def get_latest_news(
    symbol: Optional[str] = Query(None, description="Symbol to filter news by"),
    limit: int = Query(50, ge=1, le=100, description="Number of news items to return"),
    source: Optional[str] = Query(None, description="Data source (yahoo_finance, alpha_vantage)")
):
    """Get latest news items"""
    try:
        # Convert source string to DataSource enum if provided
        data_source = None
        if source:
            try:
                data_source = DataSource(source.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid data source: {source}"
                )
        
        news_items = await data_ingestion_service.get_news(
            symbol=symbol,
            limit=limit,
            source=data_source
        )
        
        # Convert to response format
        response_items = []
        for item in news_items:
            response_items.append(NewsResponse(
                headline=item.headline,
                summary=item.summary,
                url=item.url,
                source=item.source,
                published_at=item.published_at.isoformat(),
                symbols=item.symbols,
                sentiment_score=item.sentiment_score
            ))
        
        return {
            "news": response_items,
            "total": len(response_items),
            "symbol": symbol,
            "source": source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get news: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news"
        )

@router.get("/symbol/{symbol}")
async def get_news_for_symbol(
    symbol: str,
    limit: int = Query(50, ge=1, le=100, description="Number of news items to return"),
    source: Optional[str] = Query(None, description="Data source (yahoo_finance, alpha_vantage)")
):
    """Get news items for a specific symbol"""
    try:
        symbol = symbol.upper()
        
        # Convert source string to DataSource enum if provided
        data_source = None
        if source:
            try:
                data_source = DataSource(source.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid data source: {source}"
                )
        
        news_items = await data_ingestion_service.get_news(
            symbol=symbol,
            limit=limit,
            source=data_source
        )
        
        # Convert to response format
        response_items = []
        for item in news_items:
            response_items.append(NewsResponse(
                headline=item.headline,
                summary=item.summary,
                url=item.url,
                source=item.source,
                published_at=item.published_at.isoformat(),
                symbols=item.symbols,
                sentiment_score=item.sentiment_score
            ))
        
        return {
            "symbol": symbol,
            "news": response_items,
            "total": len(response_items),
            "source": source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get news for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news for symbol"
        )

@router.post("/search")
async def search_news(request: NewsSearchRequest):
    """Search for news items with filters"""
    try:
        # Convert source string to DataSource enum if provided
        data_source = None
        if request.data_source:
            try:
                data_source = DataSource(request.data_source.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid data source: {request.data_source}"
                )
        
        news_items = await data_ingestion_service.get_news(
            symbol=request.symbol,
            limit=request.limit,
            source=data_source
        )
        
        # Convert to response format
        response_items = []
        for item in news_items:
            response_items.append(NewsResponse(
                headline=item.headline,
                summary=item.summary,
                url=item.url,
                source=item.source,
                published_at=item.published_at.isoformat(),
                symbols=item.symbols,
                sentiment_score=item.sentiment_score
            ))
        
        return {
            "query": {
                "symbol": request.symbol,
                "limit": request.limit,
                "data_source": request.data_source
            },
            "news": response_items,
            "total": len(response_items)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"News search failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="News search failed"
        )

@router.get("/sources")
async def get_available_sources():
    """Get list of available news sources"""
    try:
        sources = [
            {
                "name": "Yahoo Finance",
                "key": "yahoo_finance",
                "description": "Financial news from Yahoo Finance"
            },
            {
                "name": "Alpha Vantage",
                "key": "alpha_vantage",
                "description": "Financial news with sentiment analysis from Alpha Vantage"
            }
        ]
        
        return {
            "sources": sources,
            "total": len(sources)
        }
        
    except Exception as e:
        logger.error(f"Failed to get news sources: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve news sources"
        )

@router.get("/sentiment/{symbol}")
async def get_sentiment_analysis(
    symbol: str,
    limit: int = Query(20, ge=1, le=50, description="Number of news items to analyze")
):
    """Get sentiment analysis for a symbol's news"""
    try:
        symbol = symbol.upper()
        
        # Get news with sentiment scores (Alpha Vantage provides sentiment)
        news_items = await data_ingestion_service.get_news(
            symbol=symbol,
            limit=limit,
            source=DataSource.ALPHA_VANTAGE
        )
        
        if not news_items:
            return {
                "symbol": symbol,
                "sentiment_summary": {
                    "average_sentiment": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0
                },
                "news_count": 0
            }
        
        # Calculate sentiment summary
        sentiment_scores = [item.sentiment_score for item in news_items if item.sentiment_score is not None]
        
        if sentiment_scores:
            average_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            positive_count = len([s for s in sentiment_scores if s > 0.1])
            negative_count = len([s for s in sentiment_scores if s < -0.1])
            neutral_count = len([s for s in sentiment_scores if -0.1 <= s <= 0.1])
        else:
            average_sentiment = 0
            positive_count = 0
            negative_count = 0
            neutral_count = 0
        
        return {
            "symbol": symbol,
            "sentiment_summary": {
                "average_sentiment": round(average_sentiment, 3),
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count
            },
            "news_count": len(news_items),
            "analyzed_count": len(sentiment_scores)
        }
        
    except Exception as e:
        logger.error(f"Failed to get sentiment analysis for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sentiment analysis"
        )