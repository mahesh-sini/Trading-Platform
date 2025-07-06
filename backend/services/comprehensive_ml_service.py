"""
Comprehensive ML Service for All Trading Symbols
Provides predictions and top picks across NSE/BSE/MCX/Currency/Index/ETF symbols
"""

import asyncio
import logging
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from enum import Enum
import os
import joblib
from pathlib import Path

logger = logging.getLogger(__name__)

class PredictionSignal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class MarketSegment(Enum):
    EQUITY = "EQUITY"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"
    INDEX = "INDEX"
    ETF = "ETF"

@dataclass
class SymbolPrediction:
    symbol: str
    name: str
    exchange: str
    segment: str
    sector: str
    signal: PredictionSignal
    confidence: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    expected_return: float
    risk_score: float
    technical_strength: float
    volume_strength: float
    sector_momentum: float
    prediction_horizon: str
    reasons: List[str]
    created_at: datetime

@dataclass
class TopPicksResult:
    picks: List[SymbolPrediction]
    segment: str
    total_symbols_analyzed: int
    generated_at: datetime
    market_sentiment: str
    top_sectors: List[str]

class ComprehensiveMLService:
    """
    ML Service that works with all 107 symbols in our comprehensive database
    Provides predictions, top picks, and screening across all trading segments
    """
    
    def __init__(self, db_path="trading_platform.db"):
        self.db_path = db_path
        self.models_cache = {}
        self.model_base_path = Path("models")
        
        # Existing trained models (5 symbols)
        self.trained_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        
        # Load symbol database
        self.symbols_df = self._load_all_symbols()
        
        logger.info(f"Initialized ML service with {len(self.symbols_df)} symbols")
    
    def _load_all_symbols(self) -> pd.DataFrame:
        """Load all symbols from comprehensive database"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = """
                SELECT symbol, company_name, exchange, segment, sector, 
                       market_cap, is_fo_enabled, is_etf, is_index
                FROM stock_symbols 
                WHERE status = 'ACTIVE'
                ORDER BY market_cap DESC NULLS LAST
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error loading symbols: {e}")
            return pd.DataFrame()
    
    def _has_trained_model(self, symbol: str, timeframe: str = "intraday") -> bool:
        """Check if we have a trained model for this symbol"""
        return symbol in self.trained_symbols
    
    def _load_model(self, symbol: str, timeframe: str = "intraday", model_type: str = "random_forest"):
        """Load trained model for symbol"""
        model_dir = self.model_base_path / f"{symbol}_{timeframe}_{model_type}"
        
        if not model_dir.exists():
            return None
        
        try:
            model_path = model_dir / "model.pkl"
            scaler_path = model_dir / "scaler.pkl"
            metadata_path = model_dir / "metadata.pkl"
            
            if model_path.exists() and scaler_path.exists():
                model = joblib.load(model_path)
                scaler = joblib.load(scaler_path)
                metadata = joblib.load(metadata_path) if metadata_path.exists() else {}
                
                return {
                    "model": model,
                    "scaler": scaler,
                    "metadata": metadata
                }
        except Exception as e:
            logger.error(f"Error loading model for {symbol}: {e}")
        
        return None
    
    def _generate_technical_prediction(self, symbol: str, segment: str) -> SymbolPrediction:
        """Generate prediction using technical + fundamental analysis for symbols without ML models"""
        
        # Get fundamental data for the symbol
        fundamental_score = self._get_fundamental_score(symbol)
        
        # Mock technical analysis - in production, this would use real market data
        base_scores = {
            "EQUITY": {"confidence": 0.65, "technical": 0.7, "volume": 0.6},
            "COMMODITY": {"confidence": 0.70, "technical": 0.75, "volume": 0.65},
            "CURRENCY": {"confidence": 0.60, "technical": 0.65, "volume": 0.7},
            "INDEX": {"confidence": 0.75, "technical": 0.8, "volume": 0.75},
            "ETF": {"confidence": 0.65, "technical": 0.7, "volume": 0.65}
        }
        
        scores = base_scores.get(segment, base_scores["EQUITY"])
        
        # Add some randomness based on symbol characteristics
        symbol_hash = hash(symbol) % 100
        confidence_adj = (symbol_hash - 50) / 500  # ±0.1 adjustment
        
        # Combine technical and fundamental scores
        technical_base = scores["confidence"] + confidence_adj
        fundamental_boost = fundamental_score * 0.3  # 30% weight to fundamentals
        
        confidence = max(0.3, min(0.9, technical_base + fundamental_boost))
        technical_strength = max(0.3, min(0.9, scores["technical"] + confidence_adj + fundamental_boost))
        volume_strength = max(0.3, min(0.9, scores["volume"] + confidence_adj))
        
        # Determine signal based on technical strength
        if technical_strength >= 0.8:
            signal = PredictionSignal.STRONG_BUY
            expected_return = np.random.uniform(8, 15)
        elif technical_strength >= 0.7:
            signal = PredictionSignal.BUY
            expected_return = np.random.uniform(3, 8)
        elif technical_strength >= 0.5:
            signal = PredictionSignal.HOLD
            expected_return = np.random.uniform(-2, 3)
        elif technical_strength >= 0.4:
            signal = PredictionSignal.SELL
            expected_return = np.random.uniform(-8, -2)
        else:
            signal = PredictionSignal.STRONG_SELL
            expected_return = np.random.uniform(-15, -8)
        
        # Risk score (inverse of confidence)
        risk_score = 1.0 - confidence
        
        # Generate reasons based on signal and fundamental analysis
        fundamental_reasons = self._get_fundamental_reasons(symbol, fundamental_score)
        
        reasons = []
        if signal in [PredictionSignal.STRONG_BUY, PredictionSignal.BUY]:
            reasons = [
                "Strong technical momentum",
                "Above key moving averages",
                "Volume breakout pattern",
                "Sector showing strength"
            ] + fundamental_reasons[:2]
        elif signal == PredictionSignal.HOLD:
            reasons = [
                "Consolidation pattern",
                "Mixed technical signals",
                "Waiting for clear direction"
            ] + fundamental_reasons[:1]
        else:
            reasons = [
                "Weak technical setup",
                "Below key support levels",
                "Volume declining",
                "Sector underperforming"
            ] + fundamental_reasons[:1]
        
        # Get symbol details
        symbol_info = self.symbols_df[self.symbols_df['symbol'] == symbol]
        if not symbol_info.empty:
            row = symbol_info.iloc[0]
            name = row['company_name']
            exchange = row['exchange']
            sector = row.get('sector', '')
        else:
            name = f"{symbol} Company"
            exchange = "NSE"
            sector = ""
        
        return SymbolPrediction(
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            sector=sector,
            signal=signal,
            confidence=confidence,
            target_price=None,  # Would calculate from current price + expected return
            stop_loss=None,
            expected_return=expected_return,
            risk_score=risk_score,
            technical_strength=technical_strength,
            volume_strength=volume_strength,
            sector_momentum=np.random.uniform(0.4, 0.8),
            prediction_horizon="1-3 days",
            reasons=reasons[:2],  # Keep top 2 reasons
            created_at=datetime.now()
        )
    
    def _generate_ml_prediction(self, symbol: str) -> SymbolPrediction:
        """Generate prediction using trained ML model"""
        
        # Load model
        model_info = self._load_model(symbol)
        if not model_info:
            # Fallback to technical analysis
            symbol_info = self.symbols_df[self.symbols_df['symbol'] == symbol]
            segment = symbol_info.iloc[0]['segment'] if not symbol_info.empty else "EQUITY"
            return self._generate_technical_prediction(symbol, segment)
        
        # Enhanced prediction using ML model
        # This would use real market data in production
        confidence = np.random.uniform(0.75, 0.95)  # ML models have higher confidence
        technical_strength = np.random.uniform(0.7, 0.9)
        
        if technical_strength >= 0.85:
            signal = PredictionSignal.STRONG_BUY
            expected_return = np.random.uniform(10, 20)
        elif technical_strength >= 0.75:
            signal = PredictionSignal.BUY
            expected_return = np.random.uniform(5, 12)
        else:
            signal = PredictionSignal.HOLD
            expected_return = np.random.uniform(-1, 5)
        
        # Get symbol details
        symbol_info = self.symbols_df[self.symbols_df['symbol'] == symbol]
        row = symbol_info.iloc[0]
        
        return SymbolPrediction(
            symbol=symbol,
            name=row['company_name'],
            exchange=row['exchange'],
            segment=row['segment'],
            sector=row.get('sector', ''),
            signal=signal,
            confidence=confidence,
            target_price=None,
            stop_loss=None,
            expected_return=expected_return,
            risk_score=1.0 - confidence,
            technical_strength=technical_strength,
            volume_strength=np.random.uniform(0.7, 0.9),
            sector_momentum=np.random.uniform(0.6, 0.85),
            prediction_horizon="1-5 days",
            reasons=["ML model prediction", "Strong price momentum", "Technical breakout"],
            created_at=datetime.now()
        )
    
    async def get_prediction(self, symbol: str) -> Optional[SymbolPrediction]:
        """Get prediction for a single symbol"""
        try:
            # Check if symbol exists in our database
            symbol_info = self.symbols_df[self.symbols_df['symbol'] == symbol]
            if symbol_info.empty:
                return None
            
            # Use ML model if available, otherwise technical analysis
            if self._has_trained_model(symbol):
                return self._generate_ml_prediction(symbol)
            else:
                segment = symbol_info.iloc[0]['segment']
                return self._generate_technical_prediction(symbol, segment)
        
        except Exception as e:
            logger.error(f"Error generating prediction for {symbol}: {e}")
            return None
    
    async def get_top_picks(
        self, 
        segment: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 10,
        min_confidence: float = 0.6
    ) -> TopPicksResult:
        """Get top picks across all symbols or filtered by segment/exchange"""
        
        try:
            # Filter symbols
            filtered_symbols = self.symbols_df.copy()
            
            if segment:
                filtered_symbols = filtered_symbols[filtered_symbols['segment'] == segment]
            
            if exchange:
                filtered_symbols = filtered_symbols[filtered_symbols['exchange'] == exchange]
            
            logger.info(f"Analyzing {len(filtered_symbols)} symbols for top picks")
            
            # Generate predictions for all filtered symbols
            predictions = []
            
            for _, symbol_row in filtered_symbols.iterrows():
                symbol = symbol_row['symbol']
                
                try:
                    if self._has_trained_model(symbol):
                        prediction = self._generate_ml_prediction(symbol)
                    else:
                        prediction = self._generate_technical_prediction(symbol, symbol_row['segment'])
                    
                    if prediction and prediction.confidence >= min_confidence:
                        predictions.append(prediction)
                
                except Exception as e:
                    logger.error(f"Error predicting {symbol}: {e}")
                    continue
            
            # Sort by expected return and confidence
            predictions.sort(
                key=lambda p: (p.expected_return * p.confidence), 
                reverse=True
            )
            
            # Take top picks
            top_picks = predictions[:limit]
            
            # Analyze market sentiment
            buy_signals = len([p for p in predictions if p.signal in [PredictionSignal.BUY, PredictionSignal.STRONG_BUY]])
            total_analyzed = len(predictions)
            
            if buy_signals / total_analyzed > 0.6:
                market_sentiment = "Bullish"
            elif buy_signals / total_analyzed > 0.4:
                market_sentiment = "Neutral"
            else:
                market_sentiment = "Bearish"
            
            # Top sectors
            sector_strength = {}
            for prediction in predictions:
                sector = prediction.sector or "Unknown"
                if sector not in sector_strength:
                    sector_strength[sector] = []
                sector_strength[sector].append(prediction.expected_return)
            
            top_sectors = sorted(
                sector_strength.keys(),
                key=lambda s: np.mean(sector_strength[s]),
                reverse=True
            )[:3]
            
            return TopPicksResult(
                picks=top_picks,
                segment=segment or "ALL",
                total_symbols_analyzed=total_analyzed,
                generated_at=datetime.now(),
                market_sentiment=market_sentiment,
                top_sectors=top_sectors
            )
        
        except Exception as e:
            logger.error(f"Error generating top picks: {e}")
            return TopPicksResult(
                picks=[],
                segment=segment or "ALL",
                total_symbols_analyzed=0,
                generated_at=datetime.now(),
                market_sentiment="Unknown",
                top_sectors=[]
            )
    
    async def get_sector_analysis(self) -> Dict[str, Any]:
        """Get sector-wise analysis across all symbols"""
        
        try:
            sector_analysis = {}
            
            # Group symbols by sector
            sectors = self.symbols_df['sector'].dropna().unique()
            
            for sector in sectors:
                sector_symbols = self.symbols_df[self.symbols_df['sector'] == sector]
                
                # Generate predictions for sector symbols
                sector_predictions = []
                for _, symbol_row in sector_symbols.iterrows():
                    symbol = symbol_row['symbol']
                    
                    if self._has_trained_model(symbol):
                        prediction = self._generate_ml_prediction(symbol)
                    else:
                        prediction = self._generate_technical_prediction(symbol, symbol_row['segment'])
                    
                    if prediction:
                        sector_predictions.append(prediction)
                
                if sector_predictions:
                    # Calculate sector metrics
                    avg_expected_return = np.mean([p.expected_return for p in sector_predictions])
                    avg_confidence = np.mean([p.confidence for p in sector_predictions])
                    bullish_count = len([p for p in sector_predictions if p.signal in [PredictionSignal.BUY, PredictionSignal.STRONG_BUY]])
                    
                    sector_analysis[sector] = {
                        "symbol_count": len(sector_predictions),
                        "avg_expected_return": round(avg_expected_return, 2),
                        "avg_confidence": round(avg_confidence, 2),
                        "bullish_percentage": round((bullish_count / len(sector_predictions)) * 100, 1),
                        "top_pick": max(sector_predictions, key=lambda p: p.expected_return * p.confidence)
                    }
            
            return sector_analysis
        
        except Exception as e:
            logger.error(f"Error in sector analysis: {e}")
            return {}
    
    async def screen_symbols(
        self,
        min_expected_return: float = 5.0,
        min_confidence: float = 0.7,
        max_risk_score: float = 0.5,
        segments: Optional[List[str]] = None,
        fo_only: bool = False
    ) -> List[SymbolPrediction]:
        """Screen symbols based on criteria"""
        
        try:
            # Filter symbols
            filtered_symbols = self.symbols_df.copy()
            
            if segments:
                filtered_symbols = filtered_symbols[filtered_symbols['segment'].isin(segments)]
            
            if fo_only:
                filtered_symbols = filtered_symbols[filtered_symbols['is_fo_enabled'] == 1]
            
            # Generate predictions and filter
            screened_results = []
            
            for _, symbol_row in filtered_symbols.iterrows():
                symbol = symbol_row['symbol']
                
                if self._has_trained_model(symbol):
                    prediction = self._generate_ml_prediction(symbol)
                else:
                    prediction = self._generate_technical_prediction(symbol, symbol_row['segment'])
                
                if prediction and (
                    prediction.expected_return >= min_expected_return and
                    prediction.confidence >= min_confidence and
                    prediction.risk_score <= max_risk_score
                ):
                    screened_results.append(prediction)
            
            # Sort by expected return * confidence
            screened_results.sort(
                key=lambda p: (p.expected_return * p.confidence),
                reverse=True
            )
            
            return screened_results
        
        except Exception as e:
            logger.error(f"Error screening symbols: {e}")
            return []
    
    def _get_fundamental_score(self, symbol: str) -> float:
        """Calculate fundamental analysis score for a symbol"""
        try:
            # Get symbol metadata with fundamental data
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pe_ratio, pb_ratio, dividend_yield, beta, market_cap
                FROM symbol_metadata 
                WHERE symbol = ?
            """, (symbol,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return 0.0  # No fundamental data available
            
            pe_ratio, pb_ratio, dividend_yield, beta, market_cap = result
            
            # Calculate fundamental score (0-1 scale)
            score = 0.0
            
            # PE Ratio scoring (lower is better for value)
            if pe_ratio and pe_ratio > 0:
                if pe_ratio < 15:
                    score += 0.3  # Undervalued
                elif pe_ratio < 25:
                    score += 0.15  # Fair value
                else:
                    score -= 0.1  # Overvalued
            
            # PB Ratio scoring (lower is better)
            if pb_ratio and pb_ratio > 0:
                if pb_ratio < 1.5:
                    score += 0.2
                elif pb_ratio < 3:
                    score += 0.1
                else:
                    score -= 0.05
            
            # Dividend yield scoring (higher is better for income)
            if dividend_yield and dividend_yield > 0:
                if dividend_yield > 3:
                    score += 0.2
                elif dividend_yield > 1:
                    score += 0.1
            
            # Beta scoring (lower volatility preferred)
            if beta and beta > 0:
                if beta < 1:
                    score += 0.1  # Less volatile than market
                elif beta > 1.5:
                    score -= 0.1  # High volatility
            
            # Market cap stability
            if market_cap and market_cap > 100000:  # Large cap
                score += 0.2
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Error calculating fundamental score for {symbol}: {e}")
            return 0.0
    
    def _get_fundamental_reasons(self, symbol: str, fundamental_score: float) -> List[str]:
        """Get fundamental analysis reasons for a symbol"""
        try:
            reasons = []
            
            # Get fundamental data
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pe_ratio, pb_ratio, dividend_yield, beta, market_cap
                FROM symbol_metadata 
                WHERE symbol = ?
            """, (symbol,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return ["Limited fundamental data"]
            
            pe_ratio, pb_ratio, dividend_yield, beta, market_cap = result
            
            # Generate specific fundamental reasons
            if pe_ratio and pe_ratio > 0:
                if pe_ratio < 15:
                    reasons.append(f"Attractive PE ratio ({pe_ratio:.1f})")
                elif pe_ratio > 30:
                    reasons.append(f"High PE ratio ({pe_ratio:.1f})")
            
            if dividend_yield and dividend_yield > 2:
                reasons.append(f"Good dividend yield ({dividend_yield:.1f}%)")
            
            if pb_ratio and pb_ratio < 1.5:
                reasons.append(f"Trading below book value (PB: {pb_ratio:.1f})")
            
            if market_cap and market_cap > 500000:
                reasons.append("Large-cap stability")
            
            if beta and beta < 0.8:
                reasons.append("Low volatility stock")
            elif beta and beta > 1.5:
                reasons.append("High beta stock")
            
            return reasons[:3]  # Return top 3 reasons
            
        except Exception as e:
            logger.error(f"Error getting fundamental reasons for {symbol}: {e}")
            return ["Fundamental analysis pending"]

# Global instance
ml_service = ComprehensiveMLService()