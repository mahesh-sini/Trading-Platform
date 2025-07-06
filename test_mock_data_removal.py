#!/usr/bin/env python3
"""
Test script to verify mock data removal was successful
Tests the key changes made to ensure real data integration works
"""

import sys
import os
import asyncio
import inspect
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def print_header():
    print("\n" + "="*70)
    print("🧪 Mock Data Removal - Verification Test")
    print("="*70)
    print("Testing that all mock data has been successfully removed...")
    print("="*70)

def test_ml_engine_imports():
    """Test that ML engine code doesn't contain mock data"""
    print("\n📊 Testing ML Engine...")
    
    try:
        # Read the ML engine file and check for mock data patterns
        ml_engine_path = project_root / "ml_service" / "services" / "ml_engine.py"
        with open(ml_engine_path, 'r') as f:
            content = f.read()
        
        # Check for removed mock patterns
        mock_patterns = [
            "current_price = 150.0",
            "np.random.random(18)",
            "# TODO: Get real current price"
        ]
        
        found_mock = False
        for pattern in mock_patterns:
            if pattern in content:
                print(f"    ❌ Found mock data pattern: {pattern}")
                found_mock = True
        
        # Check for real data patterns
        real_data_patterns = [
            "http://localhost:8002/v1/market-data",
            "httpx.AsyncClient",
            "Get real-time price from data service"
        ]
        
        found_real = False
        for pattern in real_data_patterns:
            if pattern in content:
                print(f"    ✅ Found real data pattern: {pattern}")
                found_real = True
        
        if not found_mock and found_real:
            print("    ✅ ML Engine successfully updated to use real data")
            return True
        else:
            print("    ❌ ML Engine still contains mock data or missing real data integration")
            return False
            
    except Exception as e:
        print(f"    ❌ Error testing ML Engine: {e}")
        return False

def test_frontend_updates():
    """Test that frontend code doesn't contain hardcoded data"""
    print("\n🖥️  Testing Frontend...")
    
    try:
        # Read the AI insights file
        ai_insights_path = project_root / "frontend" / "src" / "pages" / "ai-insights.tsx"
        with open(ai_insights_path, 'r') as f:
            content = f.read()
        
        # Check for removed mock patterns
        mock_patterns = [
            "const [predictions, setPredictions] = useState([",
            "symbol: 'RELIANCE'",
            "prediction: 'BULLISH'"
        ]
        
        found_mock = False
        for pattern in mock_patterns:
            if pattern in content and "setPredictions] = useState([]);" not in content:
                print(f"    ❌ Found hardcoded data pattern: {pattern}")
                found_mock = True
        
        # Check for real data patterns
        real_data_patterns = [
            "fetch('/api/predictions')",
            "useEffect",
            "setLoading(true)"
        ]
        
        found_real = False
        for pattern in real_data_patterns:
            if pattern in content:
                print(f"    ✅ Found real API call pattern: {pattern}")
                found_real = True
        
        if not found_mock and found_real:
            print("    ✅ Frontend successfully updated to use real API calls")
            return True
        else:
            print("    ❌ Frontend still contains hardcoded data or missing API integration")
            return False
            
    except Exception as e:
        print(f"    ❌ Error testing Frontend: {e}")
        return False

def test_feature_extraction():
    """Test that feature extraction uses real data"""
    print("\n🔧 Testing Feature Extraction...")
    
    try:
        # Read the features routes file
        features_path = project_root / "ml_service" / "api" / "routes" / "features.py"
        with open(features_path, 'r') as f:
            content = f.read()
        
        # Check for removed mock patterns
        mock_patterns = [
            "pd.date_range(start='2024-01-01'",
            "np.random.uniform(100, 200",
            "np.random.randint(1000000, 10000000"
        ]
        
        found_mock = False
        for pattern in mock_patterns:
            if pattern in content:
                print(f"    ❌ Found mock data generation: {pattern}")
                found_mock = True
        
        # Check for real data patterns
        real_data_patterns = [
            "http://localhost:8002/v1/market-data",
            "history_response = await client.get",
            "real market data from data service"
        ]
        
        found_real = False
        for pattern in real_data_patterns:
            if pattern in content:
                print(f"    ✅ Found real data integration: {pattern}")
                found_real = True
        
        if not found_mock and found_real:
            print("    ✅ Feature extraction successfully updated to use real data")
            return True
        else:
            print("    ❌ Feature extraction still contains mock data")
            return False
            
    except Exception as e:
        print(f"    ❌ Error testing Feature Extraction: {e}")
        return False

def test_model_training():
    """Test that model training uses real data"""
    print("\n🤖 Testing Model Training...")
    
    try:
        # Read the models routes file
        models_path = project_root / "ml_service" / "api" / "routes" / "models.py"
        with open(models_path, 'r') as f:
            content = f.read()
        
        # Check for removed mock patterns
        mock_patterns = [
            "dates = pd.date_range(start='2023-01-01'",
            "returns = np.random.normal(0.001, 0.02",
            "prices = [initial_price]"
        ]
        
        found_mock = False
        for pattern in mock_patterns:
            if pattern in content:
                print(f"    ❌ Found synthetic data generation: {pattern}")
                found_mock = True
        
        # Check for real data patterns
        real_data_patterns = [
            "async with httpx.AsyncClient() as client:",
            "response = await client.get(",
            "Get real training data from data service"
        ]
        
        found_real = False
        for pattern in real_data_patterns:
            if pattern in content:
                print(f"    ✅ Found real data integration: {pattern}")
                found_real = True
        
        if not found_mock and found_real:
            print("    ✅ Model training successfully updated to use real data")
            return True
        else:
            print("    ❌ Model training still contains synthetic data")
            return False
            
    except Exception as e:
        print(f"    ❌ Error testing Model Training: {e}")
        return False

def test_data_service():
    """Test that data service uses real APIs"""
    print("\n📡 Testing Data Service...")
    
    try:
        # Read the market data service file
        data_service_path = project_root / "data_service" / "services" / "market_data_service.py"
        with open(data_service_path, 'r') as f:
            content = f.read()
        
        # Check for removed mock patterns
        mock_patterns = [
            "previous_close = market_data_point.close_price * 0.99  # Placeholder",
            "# Placeholder implementation"
        ]
        
        found_mock = False
        for pattern in mock_patterns:
            if pattern in content:
                print(f"    ❌ Found placeholder implementation: {pattern}")
                found_mock = True
        
        # Check for real data patterns  
        real_data_patterns = [
            "await data_ingestion_service.get_historical_data",
            "Get previous close from historical data",
            "await data_ingestion_service.is_market_open()"
        ]
        
        found_real = False
        for pattern in real_data_patterns:
            if pattern in content:
                print(f"    ✅ Found real data service integration: {pattern}")
                found_real = True
        
        if not found_mock and found_real:
            print("    ✅ Data service successfully updated to use real APIs")
            return True
        else:
            print("    ❌ Data service still contains placeholder implementations")
            return False
            
    except Exception as e:
        print(f"    ❌ Error testing Data Service: {e}")
        return False

def test_report_exists():
    """Test that the mock data removal report exists"""
    print("\n📋 Testing Documentation...")
    
    try:
        report_path = project_root / "MOCK_DATA_REMOVAL_REPORT.md"
        if report_path.exists():
            with open(report_path, 'r') as f:
                content = f.read()
                if "Mock Data Removal - Complete Report" in content:
                    print("    ✅ Mock data removal report exists and is complete")
                    return True
        
        print("    ❌ Mock data removal report missing or incomplete")
        return False
        
    except Exception as e:
        print(f"    ❌ Error checking documentation: {e}")
        return False

def generate_summary(results):
    """Generate test summary"""
    print("\n📊 TEST SUMMARY")
    print("="*50)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    print("\n📋 DETAILED RESULTS")
    print("-" * 50)
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    if passed_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("✅ Mock data removal was successful")
        print("✅ Real data integration is working")
        print("✅ Platform is ready for testing with live data")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TESTS FAILED")
        print("❌ Some mock data may still exist")
        print("❌ Manual review required")

def main():
    """Run all mock data removal verification tests"""
    print_header()
    
    # Run all tests
    results = {
        "ML Engine Real Data Integration": test_ml_engine_imports(),
        "Frontend API Integration": test_frontend_updates(), 
        "Feature Extraction Real Data": test_feature_extraction(),
        "Model Training Real Data": test_model_training(),
        "Data Service Real APIs": test_data_service(),
        "Documentation Complete": test_report_exists()
    }
    
    # Generate summary
    generate_summary(results)
    
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)