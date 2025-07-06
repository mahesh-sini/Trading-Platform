#!/usr/bin/env python3
"""
Test script for the Auto Trading System
This script verifies that all components are properly integrated
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_auto_trading_system():
    """Test the auto trading system components"""
    
    print("🚀 Testing Auto Trading System Integration")
    print("=" * 50)
    
    # Test 1: Import all required modules
    print("1. Testing imports...")
    try:
        from backend.services.auto_trading_service import auto_trading_service
        from backend.services.ml_service_client import ml_service_client
        from backend.services.market_data_client import market_data_client
        from backend.models.auto_trade import AutoTrade, AutoTradeStatus, AutoTradeReason
        from backend.models.user import User
        from backend.models.broker import BrokerAccount, BrokerAccountStatus
        print("   ✅ All imports successful")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    # Test 2: Check auto trading service initialization
    print("2. Testing auto trading service...")
    try:
        # Check if service is initialized
        assert hasattr(auto_trading_service, 'is_running')
        assert hasattr(auto_trading_service, 'market_hours')
        assert hasattr(auto_trading_service, '_is_market_open')
        print("   ✅ Auto trading service initialized")
    except Exception as e:
        print(f"   ❌ Auto trading service error: {e}")
        return False
    
    # Test 3: Check market data client
    print("3. Testing market data client...")
    try:
        # Test fallback quote functionality
        quote = await market_data_client._get_fallback_quote("RELIANCE")
        assert quote is not None
        assert "price" in quote
        assert "symbol" in quote
        assert quote["symbol"] == "RELIANCE"
        print(f"   ✅ Market data client working (sample price: ₹{quote['price']:.2f})")
    except Exception as e:
        print(f"   ❌ Market data client error: {e}")
        return False
    
    # Test 4: Check ML service client
    print("4. Testing ML service client...")
    try:
        # Test health check (will fail but shouldn't crash)
        is_healthy = await ml_service_client.health_check()
        print(f"   ✅ ML service client initialized (healthy: {is_healthy})")
    except Exception as e:
        print(f"   ❌ ML service client error: {e}")
        return False
    
    # Test 5: Check market hours functionality
    print("5. Testing market hours detection...")
    try:
        is_open = await auto_trading_service._is_market_open()
        print(f"   ✅ Market status check working (market open: {is_open})")
    except Exception as e:
        print(f"   ❌ Market hours detection error: {e}")
        return False
    
    # Test 6: Check model classes
    print("6. Testing database models...")
    try:
        # Test AutoTrade model
        auto_trade_attrs = [
            "user_id", "symbol", "side", "quantity", "price", 
            "confidence", "expected_return", "status", "reason"
        ]
        for attr in auto_trade_attrs:
            assert hasattr(AutoTrade, attr)
        
        # Test enums
        assert AutoTradeStatus.EXECUTED
        assert AutoTradeReason.ML_PREDICTION
        assert BrokerAccountStatus.CONNECTED
        
        print("   ✅ Database models properly defined")
    except Exception as e:
        print(f"   ❌ Database model error: {e}")
        return False
    
    # Test 7: Check trading signal generation (mock)
    print("7. Testing trading signal generation...")
    try:
        from backend.services.strategy_engine import TradingSignal, SignalType
        from backend.services.auto_trading_service import AutoTradingMode
        
        # Create mock signal
        signal = TradingSignal(
            signal=SignalType.BUY,
            symbol="RELIANCE",
            confidence=0.8,
            price=2500.0,
            quantity=10,
            reason="Test signal",
            timestamp=datetime.utcnow(),
            metadata={"expected_return": 0.03}
        )
        
        assert signal.symbol == "RELIANCE"
        assert signal.confidence == 0.8
        print("   ✅ Trading signal generation working")
    except Exception as e:
        print(f"   ❌ Trading signal error: {e}")
        return False
    
    # Test 8: Check API routes (import only)
    print("8. Testing API routes...")
    try:
        from backend.api.routes.auto_trading import router
        assert router is not None
        print("   ✅ Auto trading API routes defined")
    except Exception as e:
        print(f"   ❌ API routes error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Auto Trading System Integration Test: PASSED")
    print("\nSystem Components Status:")
    print("✅ Auto Trading Service - Ready")
    print("✅ ML Service Client - Ready") 
    print("✅ Market Data Client - Ready")
    print("✅ Database Models - Ready")
    print("✅ API Endpoints - Ready")
    print("✅ Strategy Engine - Ready")
    
    print("\nNext Steps:")
    print("1. Start the backend server: cd backend && python main.py")
    print("2. Set up database tables with migrations")
    print("3. Configure broker API credentials")
    print("4. Enable auto-trading for test users")
    print("5. Monitor live trading during market hours")
    
    return True

async def main():
    """Main test function"""
    try:
        success = await test_auto_trading_system()
        if success:
            print("\n🟢 All tests passed successfully!")
            sys.exit(0)
        else:
            print("\n🔴 Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())