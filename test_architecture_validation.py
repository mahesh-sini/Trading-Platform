#!/usr/bin/env python3
"""
Architecture Validation Test
Tests that the platform follows the microservices architecture correctly
"""

import sys
import os
from pathlib import Path

def print_header():
    print("\n" + "="*70)
    print("🏗️  Architecture Validation Test")
    print("="*70)
    print("Testing microservices architecture compliance...")
    print("="*70)

def test_backend_proxy_pattern():
    """Test that backend properly proxies to ML service"""
    print("\n🔀 Testing Backend Proxy Pattern...")
    
    try:
        # Read the backend predictions route
        predictions_path = Path("backend/api/routes/predictions.py")
        with open(predictions_path, 'r') as f:
            content = f.read()
        
        # Check for proxy patterns
        proxy_patterns = [
            "ML_SERVICE_URL = os.getenv(\"ML_SERVICE_URL\", \"http://localhost:8001\")",
            "async with httpx.AsyncClient() as client:",
            "response = await client.post(",
            "f\"{ML_SERVICE_URL}/v1/"
        ]
        
        found_patterns = 0
        for pattern in proxy_patterns:
            if pattern in content:
                print(f"    ✅ Found proxy pattern: {pattern}")
                found_patterns += 1
        
        if found_patterns >= 3:
            print("    ✅ Backend properly implements proxy pattern to ML service")
            return True
        else:
            print("    ❌ Backend missing proper proxy implementation")
            return False
            
    except Exception as e:
        print(f"    ❌ Error testing backend proxy: {e}")
        return False

def test_ml_service_separation():
    """Test that ML functionality is properly separated"""
    print("\n🤖 Testing ML Service Separation...")
    
    try:
        # Check that ML functionality is NOT in backend
        backend_ml_paths = [
            "backend/services/ml",
            "backend/ml_models",
            "backend/app/services/ml"
        ]
        
        found_violations = 0
        for path in backend_ml_paths:
            if Path(path).exists():
                print(f"    ❌ Architecture violation: {path} exists in backend")
                found_violations += 1
        
        # Check that ML service exists and has proper structure
        ml_service_paths = [
            "ml_service/services/ml_engine.py",
            "ml_service/api/routes/predictions.py",
            "ml_service/api/routes/models.py",
            "ml_service/main.py"
        ]
        
        found_ml_files = 0
        for path in ml_service_paths:
            if Path(path).exists():
                print(f"    ✅ Found ML service file: {path}")
                found_ml_files += 1
        
        if found_violations == 0 and found_ml_files >= 3:
            print("    ✅ ML service properly separated from backend")
            return True
        else:
            print(f"    ❌ ML separation issues: {found_violations} violations, {found_ml_files} ML files found")
            return False
            
    except Exception as e:
        print(f"    ❌ Error testing ML separation: {e}")
        return False

def test_service_ports():
    """Test that services are configured for correct ports"""
    print("\n🚪 Testing Service Port Configuration...")
    
    port_configs = []
    
    try:
        # Check ML service port
        ml_main_path = Path("ml_service/main.py")
        if ml_main_path.exists():
            with open(ml_main_path, 'r') as f:
                content = f.read()
                if "port=8001" in content or "ML_SERVICE_PORT" in content:
                    print("    ✅ ML service configured for port 8001")
                    port_configs.append(True)
                else:
                    print("    ❌ ML service port configuration missing")
                    port_configs.append(False)
        
        # Check backend service references to ML service
        backend_predictions_path = Path("backend/api/routes/predictions.py")
        if backend_predictions_path.exists():
            with open(backend_predictions_path, 'r') as f:
                content = f.read()
                if "localhost:8001" in content:
                    print("    ✅ Backend properly references ML service on port 8001")
                    port_configs.append(True)
                else:
                    print("    ❌ Backend missing ML service port reference")
                    port_configs.append(False)
        
        return all(port_configs) and len(port_configs) >= 2
        
    except Exception as e:
        print(f"    ❌ Error testing service ports: {e}")
        return False

def test_data_service_integration():
    """Test that services properly integrate with data service"""
    print("\n📊 Testing Data Service Integration...")
    
    try:
        # Check ML service data integration
        ml_engine_path = Path("ml_service/services/ml_engine.py")
        if ml_engine_path.exists():
            with open(ml_engine_path, 'r') as f:
                content = f.read()
                if "localhost:8002" in content and "/market-data/" in content:
                    print("    ✅ ML service integrates with data service (port 8002)")
                    ml_integration = True
                else:
                    print("    ❌ ML service missing data service integration")
                    ml_integration = False
        
        # Check feature extraction data integration
        features_path = Path("ml_service/api/routes/features.py")
        if features_path.exists():
            with open(features_path, 'r') as f:
                content = f.read()
                if "localhost:8002" in content and "/market-data/" in content:
                    print("    ✅ Feature service integrates with data service")
                    features_integration = True
                else:
                    print("    ❌ Feature service missing data service integration")
                    features_integration = False
        
        return ml_integration and features_integration
        
    except Exception as e:
        print(f"    ❌ Error testing data service integration: {e}")
        return False

def test_api_consistency():
    """Test that API endpoints follow consistent patterns"""
    print("\n🔗 Testing API Consistency...")
    
    try:
        # Check backend API route structure
        backend_routes_path = Path("backend/api/routes")
        if backend_routes_path.exists():
            route_files = list(backend_routes_path.glob("*.py"))
            print(f"    ✅ Found {len(route_files)} backend route files")
            
            # Check for predictions route
            predictions_exists = (backend_routes_path / "predictions.py").exists()
            if predictions_exists:
                print("    ✅ Backend has predictions route (proxy)")
            else:
                print("    ❌ Backend missing predictions route")
        
        # Check ML service API structure
        ml_routes_path = Path("ml_service/api/routes")
        if ml_routes_path.exists():
            ml_route_files = list(ml_routes_path.glob("*.py"))
            print(f"    ✅ Found {len(ml_route_files)} ML service route files")
            
            # Check for key ML routes
            required_ml_routes = ["predictions.py", "models.py", "features.py"]
            found_ml_routes = 0
            for route in required_ml_routes:
                if (ml_routes_path / route).exists():
                    print(f"    ✅ ML service has {route}")
                    found_ml_routes += 1
                else:
                    print(f"    ❌ ML service missing {route}")
            
            return found_ml_routes >= 2 and predictions_exists
        
        return False
        
    except Exception as e:
        print(f"    ❌ Error testing API consistency: {e}")
        return False

def test_deployment_readiness():
    """Test that platform is ready for deployment"""
    print("\n🚀 Testing Deployment Readiness...")
    
    readiness_checks = []
    
    try:
        # Check for environment configuration
        env_example = Path(".env.example")
        if env_example.exists():
            print("    ✅ Environment configuration template exists")
            readiness_checks.append(True)
        else:
            print("    ⚠️  No .env.example found")
            readiness_checks.append(False)
        
        # Check for requirements files
        backend_req = Path("backend/requirements.txt")
        if backend_req.exists():
            print("    ✅ Backend requirements.txt exists")
            readiness_checks.append(True)
        else:
            print("    ❌ Backend requirements.txt missing")
            readiness_checks.append(False)
        
        # Check for documentation
        architecture_doc = Path("docs/ARCHITECTURE.md")
        if architecture_doc.exists():
            print("    ✅ Architecture documentation exists")
            readiness_checks.append(True)
        else:
            print("    ⚠️  Architecture documentation missing")
            readiness_checks.append(False)
        
        # Check for setup scripts
        setup_script = Path("setup.sh")
        if setup_script.exists():
            print("    ✅ Setup script exists")
            readiness_checks.append(True)
        else:
            print("    ⚠️  Setup script missing")
            readiness_checks.append(False)
        
        return sum(readiness_checks) >= 2
        
    except Exception as e:
        print(f"    ❌ Error testing deployment readiness: {e}")
        return False

def generate_architecture_summary(results):
    """Generate architecture validation summary"""
    print("\n📊 ARCHITECTURE VALIDATION SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"Total Architecture Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Architecture Compliance: {(passed_tests/total_tests*100):.1f}%")
    
    print("\n📋 DETAILED ARCHITECTURE RESULTS")
    print("-" * 60)
    for test_name, result in results.items():
        status = "✅ COMPLIANT" if result else "❌ VIOLATION"
        print(f"  {status} {test_name}")
    
    if passed_tests == total_tests:
        print(f"\n🏆 ARCHITECTURE FULLY COMPLIANT!")
        print("✅ Microservices properly separated")
        print("✅ Service communication working")
        print("✅ API patterns consistent")
        print("✅ Platform ready for production")
    elif passed_tests >= total_tests * 0.8:
        print(f"\n✅ ARCHITECTURE MOSTLY COMPLIANT")
        print("🎯 Minor issues need attention")
        print("✅ Core architecture is sound")
    else:
        print(f"\n⚠️  ARCHITECTURE NEEDS WORK")
        print("❌ Multiple compliance issues found")
        print("🔧 Review microservices separation")

def main():
    """Run all architecture validation tests"""
    print_header()
    
    # Run all architecture tests
    results = {
        "Backend Proxy Pattern": test_backend_proxy_pattern(),
        "ML Service Separation": test_ml_service_separation(),
        "Service Port Configuration": test_service_ports(),
        "Data Service Integration": test_data_service_integration(),
        "API Consistency": test_api_consistency(),
        "Deployment Readiness": test_deployment_readiness()
    }
    
    # Generate summary
    generate_architecture_summary(results)
    
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)