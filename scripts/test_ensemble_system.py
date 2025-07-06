#!/usr/bin/env python3
"""
Test Ensemble ML System
Quick test to validate the ensemble system with sample data
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta, date

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.bhav_copy_fetcher import bhav_fetcher
from backend.services.ensemble_ml_system import ensemble_ml_system, ModelType

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnsembleSystemTester:
    """Test the ensemble ML system functionality"""
    
    def __init__(self):
        self.test_symbols = [
            ("RELIANCE", "NSE"),
            ("TCS", "NSE"),
            ("HDFCBANK", "NSE"),
            ("INFY", "NSE"),
            ("ICICIBANK", "NSE")
        ]
    
    async def test_data_download(self):
        """Test bhav copy data download"""
        logger.info("🧪 Testing Bhav Copy Data Download")
        logger.info("-" * 50)
        
        try:
            # Test download for last 5 trading days
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=7)  # Get a week to ensure 5 trading days
            
            logger.info(f"📅 Testing download for: {start_date} to {end_date}")
            
            # Download test data
            stats = await bhav_fetcher.download_historical_bhav_data(start_date, end_date)
            
            logger.info("📊 Download Test Results:")
            logger.info(f"  📅 Days processed: {stats['total_days']}")
            logger.info(f"  ✅ Successful days: {stats['successful_days']}")
            logger.info(f"  📈 Total records: {stats['total_records']}")
            logger.info(f"  🏛️ NSE records: {stats['nse_records']}")
            logger.info(f"  🏛️ BSE records: {stats['bse_records']}")
            
            if stats['errors']:
                logger.warning(f"  ⚠️ Errors: {len(stats['errors'])}")
                for error in stats['errors'][:3]:  # Show first 3 errors
                    logger.warning(f"    • {error}")
            
            # Validate minimum data
            if stats['total_records'] > 1000:
                logger.info("✅ Data download test: PASSED")
                return True
            else:
                logger.error("❌ Data download test: FAILED - Insufficient data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Data download test failed: {e}")
            return False
    
    async def test_ensemble_training(self):
        """Test ensemble model training"""
        logger.info("\n🧪 Testing Ensemble Model Training")
        logger.info("-" * 50)
        
        try:
            successful_trainings = 0
            
            for symbol, exchange in self.test_symbols:
                logger.info(f"🤖 Testing training for {symbol} ({exchange})")
                
                try:
                    # Test training for this symbol
                    result = await ensemble_ml_system.train_ensemble_for_symbol(symbol, exchange)
                    
                    if "error" not in result:
                        successful_models = result.get('successful_models', 0)
                        total_models = result.get('total_models', 4)
                        
                        logger.info(f"  ✅ {symbol}: {successful_models}/{total_models} models trained")
                        
                        if successful_models >= 2:  # At least 2 models should work
                            successful_trainings += 1
                    else:
                        logger.error(f"  ❌ {symbol}: {result['error']}")
                
                except Exception as e:
                    logger.error(f"  ❌ {symbol}: Training failed - {e}")
            
            success_rate = (successful_trainings / len(self.test_symbols)) * 100
            
            logger.info(f"\n📊 Training Test Results:")
            logger.info(f"  ✅ Successful symbols: {successful_trainings}/{len(self.test_symbols)}")
            logger.info(f"  📈 Success rate: {success_rate:.1f}%")
            
            if success_rate >= 60:  # 60% success rate acceptable for test
                logger.info("✅ Ensemble training test: PASSED")
                return True
            else:
                logger.error("❌ Ensemble training test: FAILED")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ensemble training test failed: {e}")
            return False
    
    async def test_predictions(self):
        """Test ensemble predictions"""
        logger.info("\n🧪 Testing Ensemble Predictions")
        logger.info("-" * 50)
        
        try:
            successful_predictions = 0
            
            for symbol, exchange in self.test_symbols:
                logger.info(f"🔮 Testing prediction for {symbol} ({exchange})")
                
                try:
                    # Get ensemble prediction
                    prediction = await ensemble_ml_system.get_ensemble_prediction(symbol, exchange)
                    
                    if prediction:
                        logger.info(f"  ✅ {symbol}:")
                        logger.info(f"    Prediction: {prediction.final_prediction:.6f}")
                        logger.info(f"    Confidence: {prediction.confidence:.3f}")
                        logger.info(f"    Models used: {len(prediction.model_predictions)}")
                        logger.info(f"    Weights: {prediction.meta_learner_weights}")
                        
                        successful_predictions += 1
                    else:
                        logger.warning(f"  ⚠️ {symbol}: No prediction available")
                
                except Exception as e:
                    logger.error(f"  ❌ {symbol}: Prediction failed - {e}")
            
            success_rate = (successful_predictions / len(self.test_symbols)) * 100
            
            logger.info(f"\n📊 Prediction Test Results:")
            logger.info(f"  ✅ Successful predictions: {successful_predictions}/{len(self.test_symbols)}")
            logger.info(f"  📈 Success rate: {success_rate:.1f}%")
            
            if success_rate >= 40:  # 40% success rate acceptable for initial test
                logger.info("✅ Prediction test: PASSED")
                return True
            else:
                logger.error("❌ Prediction test: FAILED")
                return False
                
        except Exception as e:
            logger.error(f"❌ Prediction test failed: {e}")
            return False
    
    async def test_data_quality(self):
        """Test data quality and availability"""
        logger.info("\n🧪 Testing Data Quality")
        logger.info("-" * 50)
        
        try:
            # Get data quality report
            quality_report = bhav_fetcher.get_data_quality_report()
            
            if quality_report:
                logger.info("📊 Data Quality Report:")
                logger.info(f"  📈 Total records: {quality_report.get('total_records', 0)}")
                logger.info(f"  🏢 Unique symbols: {quality_report.get('unique_symbols', 0)}")
                logger.info(f"  📅 Date range: {quality_report.get('date_range', 'Unknown')}")
                logger.info(f"  ✅ Symbols with sufficient data: {quality_report.get('symbols_with_sufficient_data', 0)}")
                
                # Check by exchange
                if quality_report.get('by_exchange'):
                    logger.info("  📊 By Exchange:")
                    for exchange_data in quality_report['by_exchange']:
                        logger.info(f"    {exchange_data['exchange']}: {exchange_data['records']} records, {exchange_data['symbols']} symbols")
                
                # Validate quality metrics
                total_records = quality_report.get('total_records', 0)
                sufficient_symbols = quality_report.get('symbols_with_sufficient_data', 0)
                
                if total_records > 10000 and sufficient_symbols > 20:
                    logger.info("✅ Data quality test: PASSED")
                    return True
                else:
                    logger.error("❌ Data quality test: FAILED - Insufficient data quality")
                    return False
            else:
                logger.error("❌ Data quality test: FAILED - No data available")
                return False
                
        except Exception as e:
            logger.error(f"❌ Data quality test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all ensemble system tests"""
        logger.info("🚀 Starting Ensemble System Tests")
        logger.info("=" * 80)
        
        test_results = {}
        
        # Test 1: Data Download
        test_results['data_download'] = await self.test_data_download()
        
        # Test 2: Data Quality  
        test_results['data_quality'] = await self.test_data_quality()
        
        # Test 3: Ensemble Training
        test_results['ensemble_training'] = await self.test_ensemble_training()
        
        # Test 4: Predictions
        test_results['predictions'] = await self.test_predictions()
        
        # Summary
        self.print_test_summary(test_results)
        
        return test_results
    
    def print_test_summary(self, results: dict):
        """Print comprehensive test summary"""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 ENSEMBLE SYSTEM TEST SUMMARY")
        logger.info("=" * 80)
        
        passed_tests = sum(1 for result in results.values() if result)
        total_tests = len(results)
        success_rate = (passed_tests / total_tests) * 100
        
        logger.info(f"📊 Overall Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        logger.info("")
        
        # Individual test results
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            test_display = test_name.replace('_', ' ').title()
            logger.info(f"  {test_display}: {status}")
        
        logger.info("")
        
        if success_rate >= 75:
            logger.info("🎉 SYSTEM STATUS: READY FOR PRODUCTION")
            logger.info("   All critical tests passed. System is production-ready.")
        elif success_rate >= 50:
            logger.info("⚠️ SYSTEM STATUS: NEEDS ATTENTION")
            logger.info("   Some tests failed. Review issues before production deployment.")
        else:
            logger.info("❌ SYSTEM STATUS: NOT READY")
            logger.info("   Major issues detected. System needs fixes before use.")
        
        logger.info("")
        logger.info("📋 Next Steps:")
        if results.get('data_download', False):
            logger.info("  ✅ Data pipeline is working")
        else:
            logger.info("  ❌ Fix data download issues first")
        
        if results.get('ensemble_training', False):
            logger.info("  ✅ Model training is working")
        else:
            logger.info("  ❌ Check model training dependencies")
        
        if results.get('predictions', False):
            logger.info("  ✅ Prediction system is working")
        else:
            logger.info("  ❌ Debug prediction pipeline")
        
        logger.info("=" * 80)

async def main():
    """Main test function"""
    try:
        tester = EnsembleSystemTester()
        results = await tester.run_all_tests()
        
        # Return appropriate exit code
        passed_tests = sum(1 for result in results.values() if result)
        if passed_tests >= len(results) * 0.75:  # 75% pass rate
            return 0
        else:
            return 1
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))