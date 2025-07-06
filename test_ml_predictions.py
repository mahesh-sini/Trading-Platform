#!/usr/bin/env python3
"""
Test ML Predictions
Comprehensive test of the ML prediction system
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "ml_service"))

async def test_ml_system():
    """Test the complete ML system"""
    print("🧪 Testing ML Prediction System")
    print("=" * 50)
    
    try:
        from ml_service.services.ml_engine import MLEngine, PredictionRequest, PredictionTimeframe
        
        # Initialize ML engine
        print("🔧 Initializing ML Engine...")
        ml_engine = MLEngine()
        
        print(f"📁 Model directory: {ml_engine.model_dir}")
        print(f"📁 Directory exists: {ml_engine.model_dir.exists()}")
        
        if ml_engine.model_dir.exists():
            model_dirs = list(ml_engine.model_dir.iterdir())
            print(f"📂 Found {len(model_dirs)} model directories:")
            for model_dir in model_dirs[:5]:  # Show first 5
                print(f"    • {model_dir.name}")
        
        await ml_engine.initialize()
        
        print(f"💾 Loaded models: {len(ml_engine.models)}")
        for model_key in list(ml_engine.models.keys())[:5]:  # Show first 5
            print(f"    • {model_key}")
        
        # Test prediction
        print("\n🔮 Testing prediction...")
        request = PredictionRequest(
            symbol='RELIANCE',
            timeframe=PredictionTimeframe.INTRADAY,
            horizon='1d'
        )
        
        print(f"📊 Looking for models matching: RELIANCE_intraday_*")
        matching_models = [k for k in ml_engine.models.keys() if 'RELIANCE' in k and 'intraday' in k]
        print(f"📊 Found {len(matching_models)} matching models: {matching_models}")
        
        # Check if prediction will work
        try:
            result = await ml_engine.predict(request)
            print("✅ Prediction successful!")
            print(f"    Symbol: {result.symbol}")
            print(f"    Current Price: ₹{result.current_price:.2f}")
            print(f"    Predicted Price: ₹{result.predicted_price:.2f}")
            print(f"    Direction: {result.predicted_direction}")
            print(f"    Confidence: {result.confidence_score:.1%}")
            return True
        except Exception as e:
            print(f"❌ Prediction failed: {e}")
            return False
        finally:
            await ml_engine.shutdown()
            
    except Exception as e:
        print(f"❌ ML system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ml_system())
    sys.exit(0 if success else 1)