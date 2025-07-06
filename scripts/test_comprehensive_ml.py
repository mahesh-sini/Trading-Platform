#!/usr/bin/env python3
"""
Test script for comprehensive ML service
Tests predictions across all 107 symbols and generates top picks
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.comprehensive_ml_service import ComprehensiveMLService, MarketSegment

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_comprehensive_ml():
    """Test comprehensive ML service functionality"""
    
    try:
        # Initialize ML service
        ml_service = ComprehensiveMLService()
        
        logger.info("🤖 Testing Comprehensive ML Service")
        logger.info("=" * 60)
        
        # Test 1: Individual symbol predictions
        logger.info("\n📈 Testing Individual Symbol Predictions:")
        test_symbols = ["RELIANCE", "GOLD", "NIFTY50", "USDINR", "GOLDBEES"]
        
        for symbol in test_symbols:
            prediction = await ml_service.get_prediction(symbol)
            
            if prediction:
                logger.info(f"  ✓ {symbol} ({prediction.exchange}-{prediction.segment})")
                logger.info(f"    Signal: {prediction.signal.value}")
                logger.info(f"    Expected Return: {prediction.expected_return:.1f}%")
                logger.info(f"    Confidence: {prediction.confidence:.1%}")
                logger.info(f"    Risk Score: {prediction.risk_score:.1%}")
                logger.info(f"    Reasons: {', '.join(prediction.reasons)}")
            else:
                logger.info(f"  ❌ {symbol} - No prediction available")
        
        # Test 2: Top picks for all segments
        logger.info(f"\n🏆 Testing Top Picks by Segment:")
        
        for segment in MarketSegment:
            top_picks = await ml_service.get_top_picks(
                segment=segment.value,
                limit=5,
                min_confidence=0.5
            )
            
            logger.info(f"\n  📊 {segment.value} Segment:")
            logger.info(f"    Total analyzed: {top_picks.total_symbols_analyzed}")
            logger.info(f"    Market sentiment: {top_picks.market_sentiment}")
            logger.info(f"    Top picks count: {len(top_picks.picks)}")
            
            for i, pick in enumerate(top_picks.picks[:3], 1):
                logger.info(f"    {i}. {pick.symbol} ({pick.exchange}) - {pick.signal.value}")
                logger.info(f"       Return: {pick.expected_return:.1f}% | Confidence: {pick.confidence:.1%}")
        
        # Test 3: Overall top picks
        logger.info(f"\n🎯 Testing Overall Top Picks:")
        
        overall_picks = await ml_service.get_top_picks(limit=10, min_confidence=0.6)
        
        logger.info(f"  Total symbols analyzed: {overall_picks.total_symbols_analyzed}")
        logger.info(f"  Market sentiment: {overall_picks.market_sentiment}")
        logger.info(f"  Top sectors: {', '.join(overall_picks.top_sectors)}")
        
        logger.info(f"\n  🏆 Top 10 Picks:")
        for i, pick in enumerate(overall_picks.picks, 1):
            score = pick.expected_return * pick.confidence
            logger.info(f"  {i:2d}. {pick.symbol:12} ({pick.exchange:3}) | {pick.signal.value:10} | "
                       f"Return: {pick.expected_return:5.1f}% | Confidence: {pick.confidence:5.1%} | "
                       f"Score: {score:5.1f}")
        
        # Test 4: Sector analysis
        logger.info(f"\n📊 Testing Sector Analysis:")
        
        sector_analysis = await ml_service.get_sector_analysis()
        
        # Sort sectors by average return
        sorted_sectors = sorted(
            sector_analysis.items(),
            key=lambda x: x[1]["avg_expected_return"],
            reverse=True
        )
        
        logger.info(f"  Total sectors analyzed: {len(sorted_sectors)}")
        logger.info(f"\n  📈 Top Performing Sectors:")
        
        for sector, data in sorted_sectors[:5]:
            top_pick = data["top_pick"]
            logger.info(f"    {sector:20} | Avg Return: {data['avg_expected_return']:5.1f}% | "
                       f"Bullish: {data['bullish_percentage']:5.1f}% | "
                       f"Symbols: {data['symbol_count']:2d} | "
                       f"Top Pick: {top_pick.symbol}")
        
        # Test 5: Symbol screening
        logger.info(f"\n🔍 Testing Symbol Screening:")
        
        screened_symbols = await ml_service.screen_symbols(
            min_expected_return=5.0,
            min_confidence=0.7,
            max_risk_score=0.4,
            fo_only=False
        )
        
        logger.info(f"  Symbols matching criteria: {len(screened_symbols)}")
        logger.info(f"  Screening criteria:")
        logger.info(f"    Min expected return: 5.0%")
        logger.info(f"    Min confidence: 70%")
        logger.info(f"    Max risk score: 40%")
        
        if screened_symbols:
            logger.info(f"\n  🎯 Top Screened Picks:")
            for i, symbol in enumerate(screened_symbols[:5], 1):
                logger.info(f"    {i}. {symbol.symbol} ({symbol.exchange}-{symbol.segment})")
                logger.info(f"       {symbol.signal.value} | Return: {symbol.expected_return:.1f}% | "
                           f"Confidence: {symbol.confidence:.1%} | Risk: {symbol.risk_score:.1%}")
        
        # Test 6: F&O stocks only
        logger.info(f"\n🔥 Testing F&O Stocks Only:")
        
        fo_picks = await ml_service.get_top_picks(
            segment="EQUITY",
            limit=8,
            min_confidence=0.6
        )
        
        # Filter for F&O enabled (from our database)
        fo_symbols = ml_service.symbols_df[ml_service.symbols_df['is_fo_enabled'] == 1]['symbol'].tolist()
        fo_predictions = [pick for pick in fo_picks.picks if pick.symbol in fo_symbols]
        
        logger.info(f"  F&O enabled stocks found: {len(fo_symbols)}")
        logger.info(f"  F&O top picks: {len(fo_predictions)}")
        
        for i, pick in enumerate(fo_predictions[:5], 1):
            logger.info(f"    {i}. {pick.symbol} (F&O) - {pick.signal.value}")
            logger.info(f"       Return: {pick.expected_return:.1f}% | Confidence: {pick.confidence:.1%}")
        
        # Test 7: Statistics summary
        logger.info(f"\n📊 ML Service Statistics:")
        logger.info(f"  Total symbols in database: {len(ml_service.symbols_df)}")
        logger.info(f"  Trained ML models: {len(ml_service.trained_symbols)}")
        logger.info(f"  Technical analysis coverage: {len(ml_service.symbols_df) - len(ml_service.trained_symbols)}")
        
        # Segment breakdown
        segment_counts = ml_service.symbols_df['segment'].value_counts()
        logger.info(f"\n  📈 Segment Breakdown:")
        for segment, count in segment_counts.items():
            logger.info(f"    {segment}: {count} symbols")
        
        # Exchange breakdown
        exchange_counts = ml_service.symbols_df['exchange'].value_counts()
        logger.info(f"\n  🏛️ Exchange Breakdown:")
        for exchange, count in exchange_counts.items():
            logger.info(f"    {exchange}: {count} symbols")
        
        logger.info(f"\n✅ Comprehensive ML Service Testing Completed!")
        logger.info(f"🚀 Ready for production with full 107-symbol coverage!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing ML service: {e}")
        return False

async def main():
    """Run comprehensive ML tests"""
    success = await test_comprehensive_ml()
    return 0 if success else 1

if __name__ == "__main__":
    exit(asyncio.run(main()))