#!/usr/bin/env python3
"""
ML Status Checker
Checks the current state of ML models and training data
"""

import sys
import os
from pathlib import Path
import json

def print_header():
    print("\n" + "="*70)
    print("🤖 ML Platform Status Check")
    print("="*70)
    print("Checking current state of ML models and training...")
    print("="*70)

def check_model_directories():
    """Check for model storage directories"""
    print("\n📁 Checking Model Directories...")
    
    potential_model_dirs = [
        "ml_service/models",
        "backend/models", 
        "models",
        "ml_models"
    ]
    
    found_dirs = []
    for dir_path in potential_model_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"    ✅ Found directory: {dir_path}")
            
            # Check contents
            files = list(path.glob("*"))
            if files:
                print(f"        📄 Contains {len(files)} items:")
                for file in files[:5]:  # Show first 5
                    print(f"          • {file.name}")
                if len(files) > 5:
                    print(f"          ... and {len(files) - 5} more")
            else:
                print(f"        📭 Directory is empty")
            
            found_dirs.append(dir_path)
        else:
            print(f"    ❌ Not found: {dir_path}")
    
    return found_dirs

def check_trained_models():
    """Check for trained model files"""
    print("\n🤖 Checking for Trained Models...")
    
    model_extensions = ["*.pkl", "*.h5", "*.joblib", "*.model", "*.pt"]
    found_models = []
    
    for ext in model_extensions:
        models = list(Path(".").rglob(ext))
        # Filter out virtual environment files
        models = [m for m in models if "trading_env" not in str(m) and "node_modules" not in str(m)]
        
        if models:
            print(f"    ✅ Found {len(models)} {ext} files:")
            for model in models[:3]:  # Show first 3
                print(f"        📄 {model}")
            if len(models) > 3:
                print(f"        ... and {len(models) - 3} more")
            found_models.extend(models)
    
    if not found_models:
        print("    ❌ No trained model files found")
        print("    💡 This means the ML system has no trained models to make predictions")
    
    return found_models

def check_ml_engine_state():
    """Check ML engine configuration"""
    print("\n⚙️  Checking ML Engine Configuration...")
    
    try:
        # Read ML engine file
        ml_engine_path = Path("ml_service/services/ml_engine.py")
        if ml_engine_path.exists():
            with open(ml_engine_path, 'r') as f:
                content = f.read()
            
            # Check key components
            checks = {
                "MLEngine class": "class MLEngine:" in content,
                "Model loading": "load_models" in content,
                "Model training": "train_model" in content,
                "Prediction method": "async def predict" in content,
                "Model directory": "self.model_dir" in content
            }
            
            for check, result in checks.items():
                status = "✅" if result else "❌"
                print(f"    {status} {check}")
            
            return all(checks.values())
        else:
            print("    ❌ ML engine file not found")
            return False
            
    except Exception as e:
        print(f"    ❌ Error checking ML engine: {e}")
        return False

def check_prediction_flow():
    """Check how predictions currently work"""
    print("\n🔮 Checking Prediction Flow...")
    
    try:
        # Read prediction logic
        ml_engine_path = Path("ml_service/services/ml_engine.py")
        with open(ml_engine_path, 'r') as f:
            content = f.read()
        
        # Check for the "no model" error
        if "No trained model found" in content:
            print("    ⚠️  Prediction flow will fail if no models are trained")
            print("        📄 Line found: 'No trained model found for {symbol} {timeframe}'")
            print("        💡 This explains why predictions don't work yet")
        
        # Check for model search logic
        if "model_candidates" in content:
            print("    ✅ Model search logic exists")
            print("        📋 Searches for models by symbol/timeframe/type")
        
        # Check for real data integration
        if "httpx.AsyncClient" in content:
            print("    ✅ Real data integration configured")
            print("        📡 Uses data service for live market data")
        
        return True
        
    except Exception as e:
        print(f"    ❌ Error checking prediction flow: {e}")
        return False

def check_training_capability():
    """Check if training is possible"""
    print("\n🎓 Checking Training Capability...")
    
    try:
        # Check if training dependencies are available
        dependencies = {
            "pandas": False,
            "numpy": False, 
            "scikit-learn": False,
            "tensorflow": False,
            "xgboost": False
        }
        
        # Check requirements.txt
        req_path = Path("ml_service/requirements.txt")
        if req_path.exists():
            with open(req_path, 'r') as f:
                requirements = f.read()
            
            for dep in dependencies:
                if dep in requirements or dep.replace("-", "_") in requirements:
                    dependencies[dep] = True
        
        print("    📦 ML Dependencies:")
        for dep, available in dependencies.items():
            status = "✅" if available else "❌"
            print(f"        {status} {dep}")
        
        available_count = sum(dependencies.values())
        print(f"    📊 {available_count}/{len(dependencies)} dependencies configured")
        
        return available_count >= 3  # Need at least 3 key dependencies
        
    except Exception as e:
        print(f"    ❌ Error checking training capability: {e}")
        return False

def generate_recommendations():
    """Generate recommendations based on findings"""
    print("\n💡 RECOMMENDATIONS")
    print("="*50)
    
    print("🎯 To make the ML platform functional:")
    print("")
    print("1. 🤖 TRAIN INITIAL MODELS")
    print("   python train_initial_models.py")
    print("   • Creates trained models for key Indian stocks")
    print("   • Uses realistic synthetic data for bootstrapping")
    print("   • Enables predictions to work immediately")
    print("")
    print("2. 📊 SETUP REAL DATA TRAINING")
    print("   • Configure API credentials for live data")
    print("   • Set up automated retraining with market data")
    print("   • Implement model performance monitoring")
    print("")
    print("3. 🔄 CONTINUOUS IMPROVEMENT")
    print("   • Schedule daily/weekly model retraining")
    print("   • Add more sophisticated ML models (LSTM, etc.)")
    print("   • Implement A/B testing for model comparison")

def main():
    """Check ML platform status"""
    print_header()
    
    # Run all checks
    model_dirs = check_model_directories()
    trained_models = check_trained_models()
    engine_ok = check_ml_engine_state()
    prediction_ok = check_prediction_flow()
    training_ok = check_training_capability()
    
    # Generate status summary
    print("\n📊 ML PLATFORM STATUS SUMMARY")
    print("="*50)
    
    print(f"Model Directories: {len(model_dirs)} found")
    print(f"Trained Models: {len(trained_models)} found")
    print(f"ML Engine: {'✅ Configured' if engine_ok else '❌ Issues'}")
    print(f"Prediction Flow: {'✅ Ready' if prediction_ok else '❌ Blocked'}")
    print(f"Training Capability: {'✅ Available' if training_ok else '❌ Missing deps'}")
    
    if len(trained_models) == 0:
        print(f"\n⚠️  CRITICAL ISSUE IDENTIFIED")
        print(f"❌ No trained models available")
        print(f"❌ Predictions will fail with 'No trained model found' error")
        print(f"❌ ML platform is not functional")
        print(f"")
        print(f"🔧 IMMEDIATE ACTION REQUIRED:")
        print(f"   Run: python train_initial_models.py")
    else:
        print(f"\n✅ ML PLATFORM IS FUNCTIONAL")
        print(f"🎉 {len(trained_models)} trained models available")
        print(f"🚀 Predictions should work")
    
    generate_recommendations()
    
    return 0 if len(trained_models) > 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)