"""
Comprehensive ML Insights API
Provides predictions, top picks, and screening across all 107 trading symbols
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
from ...services.comprehensive_ml_service import ml_service, PredictionSignal, MarketSegment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["ml_insights"])

@router.get("/prediction/{symbol}")
async def get_symbol_prediction(
    symbol: str,
    exchange: Optional[str] = Query(None, description="Exchange filter (NSE,BSE,MCX)")
):
    """
    Get ML prediction for a specific symbol
    
    Returns prediction with confidence, signal, expected return, and technical analysis
    """
    try:
        prediction = await ml_service.get_prediction(symbol.upper())
        
        if not prediction:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "prediction": {
                "signal": prediction.signal.value,
                "confidence": round(prediction.confidence, 3),
                "expected_return": round(prediction.expected_return, 2),
                "risk_score": round(prediction.risk_score, 3),
                "technical_strength": round(prediction.technical_strength, 3),
                "volume_strength": round(prediction.volume_strength, 3),
                "sector_momentum": round(prediction.sector_momentum, 3),
                "prediction_horizon": prediction.prediction_horizon,
                "reasons": prediction.reasons,
                "symbol_info": {
                    "name": prediction.name,
                    "exchange": prediction.exchange,
                    "segment": prediction.segment,
                    "sector": prediction.sector
                },
                "generated_at": prediction.created_at.isoformat()
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prediction for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Error generating prediction")

@router.get("/top-picks")
async def get_top_picks(
    segment: Optional[str] = Query(None, description="Segment filter (EQUITY,COMMODITY,CURRENCY,INDEX,ETF)"),
    exchange: Optional[str] = Query(None, description="Exchange filter (NSE,BSE,MCX)"),
    limit: int = Query(10, description="Number of top picks"),
    min_confidence: float = Query(0.6, description="Minimum confidence threshold")
):
    """
    Get top stock picks across all symbols with ML analysis
    
    Returns ranked list of best opportunities based on:
    - Expected return
    - Confidence score  
    - Risk-adjusted ranking
    - Technical strength
    """
    try:
        if segment and segment.upper() not in [s.value for s in MarketSegment]:
            raise HTTPException(status_code=400, detail=f"Invalid segment: {segment}")
        
        top_picks_result = await ml_service.get_top_picks(
            segment=segment.upper() if segment else None,
            exchange=exchange.upper() if exchange else None,
            limit=min(limit, 25),  # Cap at 25
            min_confidence=max(0.1, min(1.0, min_confidence))
        )
        
        # Format response
        picks_data = []
        for pick in top_picks_result.picks:
            picks_data.append({
                "rank": len(picks_data) + 1,
                "symbol": pick.symbol,
                "name": pick.name,
                "exchange": pick.exchange,
                "segment": pick.segment,
                "sector": pick.sector,
                "signal": pick.signal.value,
                "confidence": round(pick.confidence, 3),
                "expected_return": round(pick.expected_return, 2),
                "risk_score": round(pick.risk_score, 3),
                "technical_strength": round(pick.technical_strength, 3),
                "reasons": pick.reasons,
                "score": round(pick.expected_return * pick.confidence, 2)
            })
        
        return {
            "success": True,
            "top_picks": picks_data,
            "analysis": {
                "segment": top_picks_result.segment,
                "total_symbols_analyzed": top_picks_result.total_symbols_analyzed,
                "market_sentiment": top_picks_result.market_sentiment,
                "top_sectors": top_picks_result.top_sectors,
                "generated_at": top_picks_result.generated_at.isoformat()
            },
            "filters": {
                "segment": segment,
                "exchange": exchange,
                "min_confidence": min_confidence,
                "limit": limit
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top picks: {e}")
        raise HTTPException(status_code=500, detail="Error generating top picks")

@router.get("/sector-analysis")
async def get_sector_analysis():
    """
    Get comprehensive sector-wise analysis across all symbols
    
    Returns sector performance, top picks per sector, and trends
    """
    try:
        sector_analysis = await ml_service.get_sector_analysis()
        
        # Format response
        sectors_data = []
        for sector, data in sector_analysis.items():
            top_pick = data["top_pick"]
            
            sectors_data.append({
                "sector": sector,
                "metrics": {
                    "symbol_count": data["symbol_count"],
                    "avg_expected_return": data["avg_expected_return"],
                    "avg_confidence": data["avg_confidence"],
                    "bullish_percentage": data["bullish_percentage"]
                },
                "top_pick": {
                    "symbol": top_pick.symbol,
                    "name": top_pick.name,
                    "exchange": top_pick.exchange,
                    "signal": top_pick.signal.value,
                    "expected_return": round(top_pick.expected_return, 2),
                    "confidence": round(top_pick.confidence, 3)
                }
            })
        
        # Sort by average expected return
        sectors_data.sort(key=lambda x: x["metrics"]["avg_expected_return"], reverse=True)
        
        return {
            "success": True,
            "sector_analysis": sectors_data,
            "summary": {
                "total_sectors": len(sectors_data),
                "best_performing_sector": sectors_data[0]["sector"] if sectors_data else None,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    except Exception as e:
        logger.error(f"Error in sector analysis: {e}")
        raise HTTPException(status_code=500, detail="Error generating sector analysis")

@router.get("/screen")
async def screen_symbols(
    min_expected_return: float = Query(5.0, description="Minimum expected return (%)"),
    min_confidence: float = Query(0.7, description="Minimum confidence score"),
    max_risk_score: float = Query(0.5, description="Maximum risk score"),
    segments: Optional[str] = Query(None, description="Comma-separated segments"),
    fo_only: bool = Query(False, description="F&O enabled stocks only"),
    limit: int = Query(20, description="Maximum results")
):
    """
    Screen symbols based on ML criteria
    
    Find symbols matching specific risk/return profiles across all markets
    """
    try:
        segment_list = None
        if segments:
            segment_list = [s.strip().upper() for s in segments.split(",")]
            # Validate segments
            invalid_segments = [s for s in segment_list if s not in [seg.value for seg in MarketSegment]]
            if invalid_segments:
                raise HTTPException(status_code=400, detail=f"Invalid segments: {invalid_segments}")
        
        screened_symbols = await ml_service.screen_symbols(
            min_expected_return=min_expected_return,
            min_confidence=min_confidence,
            max_risk_score=max_risk_score,
            segments=segment_list,
            fo_only=fo_only
        )
        
        # Format response
        results_data = []
        for symbol in screened_symbols[:limit]:
            results_data.append({
                "symbol": symbol.symbol,
                "name": symbol.name,
                "exchange": symbol.exchange,
                "segment": symbol.segment,
                "sector": symbol.sector,
                "signal": symbol.signal.value,
                "expected_return": round(symbol.expected_return, 2),
                "confidence": round(symbol.confidence, 3),
                "risk_score": round(symbol.risk_score, 3),
                "technical_strength": round(symbol.technical_strength, 3),
                "reasons": symbol.reasons,
                "score": round(symbol.expected_return * symbol.confidence, 2)
            })
        
        return {
            "success": True,
            "screened_symbols": results_data,
            "screening_criteria": {
                "min_expected_return": min_expected_return,
                "min_confidence": min_confidence,
                "max_risk_score": max_risk_score,
                "segments": segment_list,
                "fo_only": fo_only
            },
            "summary": {
                "symbols_found": len(results_data),
                "total_screened": len(screened_symbols),
                "avg_expected_return": round(np.mean([s.expected_return for s in screened_symbols]), 2) if screened_symbols else 0,
                "avg_confidence": round(np.mean([s.confidence for s in screened_symbols]), 3) if screened_symbols else 0
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error screening symbols: {e}")
        raise HTTPException(status_code=500, detail="Error screening symbols")

@router.get("/market-overview")
async def get_market_overview():
    """
    Get comprehensive market overview with ML insights across all segments
    """
    try:
        # Get top picks for each segment
        segments_overview = {}
        
        for segment in MarketSegment:
            segment_picks = await ml_service.get_top_picks(
                segment=segment.value,
                limit=5,
                min_confidence=0.5
            )
            
            segments_overview[segment.value] = {
                "total_symbols": segment_picks.total_symbols_analyzed,
                "market_sentiment": segment_picks.market_sentiment,
                "top_picks_count": len(segment_picks.picks),
                "best_pick": {
                    "symbol": segment_picks.picks[0].symbol,
                    "expected_return": round(segment_picks.picks[0].expected_return, 2),
                    "confidence": round(segment_picks.picks[0].confidence, 3)
                } if segment_picks.picks else None
            }
        
        # Overall market sentiment
        all_picks = await ml_service.get_top_picks(limit=50, min_confidence=0.1)
        
        return {
            "success": True,
            "market_overview": {
                "overall_sentiment": all_picks.market_sentiment,
                "total_symbols_tracked": all_picks.total_symbols_analyzed,
                "top_sectors": all_picks.top_sectors,
                "segments": segments_overview
            },
            "highlights": {
                "best_equity_pick": segments_overview.get("EQUITY", {}).get("best_pick"),
                "best_commodity_pick": segments_overview.get("COMMODITY", {}).get("best_pick"),
                "best_currency_pick": segments_overview.get("CURRENCY", {}).get("best_pick")
            },
            "generated_at": all_picks.generated_at.isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error generating market overview: {e}")
        raise HTTPException(status_code=500, detail="Error generating market overview")

@router.get("/stats")
async def get_ml_stats():
    """Get ML service statistics and coverage"""
    try:
        # Load symbol counts
        total_symbols = len(ml_service.symbols_df)
        trained_models = len(ml_service.trained_symbols)
        
        # Segment breakdown
        segment_counts = ml_service.symbols_df['segment'].value_counts().to_dict()
        exchange_counts = ml_service.symbols_df['exchange'].value_counts().to_dict()
        
        return {
            "success": True,
            "ml_coverage": {
                "total_symbols": total_symbols,
                "trained_ml_models": trained_models,
                "technical_analysis_coverage": total_symbols - trained_models,
                "coverage_percentage": round((total_symbols / total_symbols) * 100, 1)
            },
            "database_breakdown": {
                "by_segment": segment_counts,
                "by_exchange": exchange_counts
            },
            "model_types": {
                "ml_models": ["Random Forest", "XGBoost"] if trained_models > 0 else [],
                "technical_analysis": "RSI, MACD, Moving Averages, Bollinger Bands",
                "prediction_methods": "ML + Technical Analysis Hybrid"
            },
            "capabilities": [
                "Individual symbol predictions",
                "Top picks across all segments", 
                "Sector-wise analysis",
                "Risk-based screening",
                "F&O stock filtering",
                "Multi-exchange support"
            ]
        }
    
    except Exception as e:
        logger.error(f"Error getting ML stats: {e}")
        raise HTTPException(status_code=500, detail="Error fetching ML statistics")

# Import datetime for sector analysis
from datetime import datetime
import numpy as np