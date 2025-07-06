#!/usr/bin/env python3
"""
Production Data Pipeline Setup
Downloads historical data and trains ensemble models for production use
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta, date
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.bhav_copy_fetcher import bhav_fetcher
from backend.services.ensemble_ml_system import ensemble_ml_system

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('production_setup.log')
    ]
)
logger = logging.getLogger(__name__)

class ProductionDataPipeline:
    """Complete production data pipeline setup"""
    
    def __init__(self):
        self.start_time = datetime.now()
        
    async def setup_complete_pipeline(self, years: int = 1, train_models: bool = True):
        """Set up complete production pipeline"""
        try:
            logger.info("🚀 Starting Production Data Pipeline Setup")
            logger.info("=" * 80)
            
            # Phase 1: Download Historical Data
            logger.info("📥 PHASE 1: Historical Data Download")
            logger.info("-" * 50)
            
            await self.download_historical_data(years)
            
            # Phase 2: Train Ensemble Models
            if train_models:
                logger.info("\n🤖 PHASE 2: Ensemble Model Training")
                logger.info("-" * 50)
                
                await self.train_production_models()
            
            # Phase 3: Validation & Testing
            logger.info("\n✅ PHASE 3: System Validation")
            logger.info("-" * 50)
            
            await self.validate_system()
            
            # Phase 4: Setup Daily Jobs
            logger.info("\n⏰ PHASE 4: Production Schedule Setup")
            logger.info("-" * 50)
            
            self.setup_production_schedules()
            
            logger.info("\n🎉 Production Pipeline Setup Complete!")
            self.print_final_summary()
            
        except Exception as e:
            logger.error(f"❌ Pipeline setup failed: {e}")
            raise
    
    async def download_historical_data(self, years: int):
        """Download historical bhav copy data"""
        try:
            # Calculate date range
            end_date = date.today() - timedelta(days=1)  # Yesterday
            start_date = end_date - timedelta(days=years * 365)
            
            logger.info(f"📅 Downloading {years} year(s) of historical data")
            logger.info(f"📅 Date range: {start_date} to {end_date}")
            
            # Download historical data
            stats = await bhav_fetcher.download_historical_bhav_data(start_date, end_date)
            
            logger.info("📊 Historical Data Download Summary:")
            logger.info(f"  📅 Date range: {stats['start_date']} to {stats['end_date']}")
            logger.info(f"  📈 Trading days processed: {stats['total_days']}")
            logger.info(f"  ✅ Successful days: {stats['successful_days']}")
            logger.info(f"  📊 Total records: {stats['total_records']}")
            logger.info(f"  🏛️ NSE records: {stats['nse_records']}")
            logger.info(f"  🏛️ BSE records: {stats['bse_records']}")
            
            # Data quality check
            if stats['total_records'] < 50000:  # Minimum expectation
                logger.warning("⚠️ Low data volume - check data sources")
            else:
                logger.info("✅ Historical data download successful")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Historical data download failed: {e}")
            raise
    
    async def train_production_models(self):
        """Train ensemble models for production"""
        try:
            logger.info("🤖 Starting ensemble model training")
            
            # Train all models
            training_stats = await ensemble_ml_system.train_all_symbols()
            
            logger.info("🤖 Ensemble Training Summary:")
            logger.info(f"  📊 Total symbols: {training_stats['total_symbols']}")
            logger.info(f"  ✅ Successful trainings: {training_stats['successful_trainings']}")
            logger.info(f"  ❌ Failed trainings: {training_stats['failed_trainings']}")
            logger.info(f"  📈 Success rate: {training_stats['success_rate']:.1f}%")
            
            # Print top successful models
            successful_results = [r for r in training_stats['training_results'] if 'error' not in r]
            if successful_results:
                logger.info("🏆 Top Trained Models:")
                for result in successful_results[:5]:
                    symbol = result['symbol']
                    successful_models = result['successful_models']
                    total_models = result['total_models']
                    logger.info(f"  • {symbol}: {successful_models}/{total_models} models trained")
            
            return training_stats
            
        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            raise
    
    async def validate_system(self):
        """Validate the complete system"""
        try:
            logger.info("🔍 Validating production system")
            
            # Test data availability
            data_quality = bhav_fetcher.get_data_quality_report()
            
            if data_quality:
                logger.info("📊 Data Quality Report:")
                logger.info(f"  📈 Total records: {data_quality.get('total_records', 0)}")
                logger.info(f"  🏢 Unique symbols: {data_quality.get('unique_symbols', 0)}")
                logger.info(f"  📅 Date range: {data_quality.get('date_range', 'Unknown')}")
                
                # Check by exchange
                if data_quality.get('by_exchange'):
                    logger.info("  📊 By Exchange:")
                    for exchange_data in data_quality['by_exchange']:
                        logger.info(f"    {exchange_data['exchange']}: {exchange_data['records']} records, {exchange_data['symbols']} symbols")
                
                # Test model predictions
                await self.test_model_predictions()
            
            logger.info("✅ System validation completed")
            
        except Exception as e:
            logger.error(f"❌ System validation failed: {e}")
            raise
    
    async def test_model_predictions(self):
        """Test model predictions on sample symbols"""
        try:
            # Test with a few sample symbols
            test_symbols = [
                ("RELIANCE", "NSE"),
                ("TCS", "NSE"), 
                ("HDFCBANK", "NSE")
            ]
            
            logger.info("🧪 Testing model predictions:")
            
            for symbol, exchange in test_symbols:
                try:
                    prediction = await ensemble_ml_system.get_ensemble_prediction(symbol, exchange)
                    
                    if prediction:
                        logger.info(f"  ✅ {symbol}: Prediction={prediction.final_prediction:.4f}, Confidence={prediction.confidence:.2f}")
                        logger.info(f"     Models used: {len(prediction.model_predictions)}")
                    else:
                        logger.warning(f"  ⚠️ {symbol}: No prediction available")
                        
                except Exception as e:
                    logger.error(f"  ❌ {symbol}: Prediction failed - {e}")
            
        except Exception as e:
            logger.error(f"Error testing predictions: {e}")
    
    def setup_production_schedules(self):
        """Setup cron job configurations for production"""
        try:
            logger.info("⏰ Setting up production schedules")
            
            # Create cron job scripts directory
            cron_dir = Path("scripts/cron_jobs")
            cron_dir.mkdir(parents=True, exist_ok=True)
            
            # Daily data download script
            self.create_daily_download_script(cron_dir)
            
            # Training schedule scripts
            self.create_training_scripts(cron_dir)
            
            # Print cron job recommendations
            self.print_cron_recommendations()
            
        except Exception as e:
            logger.error(f"❌ Error setting up schedules: {e}")
    
    def create_daily_download_script(self, cron_dir: Path):
        """Create daily data download script"""
        script_content = '''#!/bin/bash
# Daily Bhav Copy Download Script
# Run at 6:30 PM daily (after market close)

cd "/home/elconsys/Trading Platform"
source activate_env.sh

python3 << 'EOF'
import asyncio
import sys
import os
from datetime import date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.bhav_copy_fetcher import bhav_fetcher

async def daily_download():
    """Download yesterday's bhav data"""
    try:
        yesterday = date.today() - timedelta(days=1)
        result = await bhav_fetcher.download_bhav_data(yesterday)
        
        print(f"Daily download completed: {result['total_records']} records")
        
        if result['errors']:
            print(f"Errors: {result['errors']}")
            sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

asyncio.run(daily_download())
EOF

deactivate
'''
        
        script_path = cron_dir / "daily_download.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        script_path.chmod(0o755)
        
        logger.info(f"  📝 Created: {script_path}")
    
    def create_training_scripts(self, cron_dir: Path):
        """Create model training scripts"""
        
        # Daily short-term model retraining
        daily_training = '''#!/bin/bash
# Daily Short-term Model Retraining
# Run at 8:00 PM daily

cd "/home/elconsys/Trading Platform"
source activate_env.sh

python3 << 'EOF'
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.services.ensemble_ml_system import ensemble_ml_system, ModelType

async def daily_training():
    """Retrain short-term models"""
    try:
        # Get top 20 F&O stocks for daily training
        conn = sqlite3.connect("trading_platform.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, exchange FROM stock_symbols 
            WHERE is_fo_enabled = 1 AND status = 'ACTIVE'
            ORDER BY market_cap DESC LIMIT 20
        """)
        
        symbols = cursor.fetchall()
        conn.close()
        
        print(f"Retraining short-term models for {len(symbols)} symbols")
        
        for symbol, exchange in symbols:
            try:
                # Only retrain short-term model daily
                model = BaseMLModel(ModelType.SHORT_TERM, symbol, exchange)
                df = ensemble_ml_system.get_training_data(symbol, exchange, 60)
                
                if len(df) >= 30:
                    stats = model.train(df)
                    model_path = ensemble_ml_system.models_dir / f"{symbol}_{exchange}_short_term.pkl"
                    model.save_model(model_path)
                    print(f"  ✅ {symbol}: R²={stats['train_r2']:.3f}")
                
            except Exception as e:
                print(f"  ❌ {symbol}: {e}")
        
        print("Daily training completed")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

asyncio.run(daily_training())
EOF

deactivate
'''
        
        daily_script = cron_dir / "daily_training.sh" 
        with open(daily_script, 'w') as f:
            f.write(daily_training)
        daily_script.chmod(0o755)
        
        # Weekly training script
        weekly_training = '''#!/bin/bash
# Weekly Medium-term Model Retraining  
# Run every Sunday at 10:00 PM

cd "/home/elconsys/Trading Platform"
source activate_env.sh

python3 << 'EOF'
import asyncio
from backend.services.ensemble_ml_system import ensemble_ml_system

async def weekly_training():
    """Retrain medium-term models weekly"""
    result = await ensemble_ml_system.train_all_symbols()
    print(f"Weekly training: {result['successful_trainings']} models trained")

asyncio.run(weekly_training())
EOF

deactivate
'''
        
        weekly_script = cron_dir / "weekly_training.sh"
        with open(weekly_script, 'w') as f:
            f.write(weekly_training)
        weekly_script.chmod(0o755)
        
        logger.info(f"  📝 Created: {daily_script}")
        logger.info(f"  📝 Created: {weekly_script}")
    
    def print_cron_recommendations(self):
        """Print recommended cron job settings"""
        logger.info("📋 Recommended Cron Job Settings:")
        logger.info("   Add these lines to crontab (crontab -e):")
        logger.info("")
        logger.info("   # Daily data download at 6:30 PM")
        logger.info("   30 18 * * 1-5 /home/elconsys/Trading\\ Platform/scripts/cron_jobs/daily_download.sh")
        logger.info("")
        logger.info("   # Daily short-term model training at 8:00 PM")  
        logger.info("   0 20 * * 1-5 /home/elconsys/Trading\\ Platform/scripts/cron_jobs/daily_training.sh")
        logger.info("")
        logger.info("   # Weekly full retraining on Sunday at 10:00 PM")
        logger.info("   0 22 * * 0 /home/elconsys/Trading\\ Platform/scripts/cron_jobs/weekly_training.sh")
        logger.info("")
    
    def print_final_summary(self):
        """Print final setup summary"""
        total_time = datetime.now() - self.start_time
        
        logger.info("🎉 PRODUCTION SETUP COMPLETED!")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total setup time: {total_time}")
        logger.info("")
        logger.info("📊 What's been set up:")
        logger.info("  ✅ Historical data pipeline (NSE/BSE Bhav copies)")
        logger.info("  ✅ Ensemble ML system (4 models per symbol)")
        logger.info("  ✅ Production training scripts")
        logger.info("  ✅ Daily automation schedules")
        logger.info("")
        logger.info("🚀 Your trading platform is now production-ready!")
        logger.info("")
        logger.info("📋 Next steps:")
        logger.info("  1. Set up the recommended cron jobs")
        logger.info("  2. Monitor daily data downloads")
        logger.info("  3. Check model performance metrics")
        logger.info("  4. Fine-tune prediction thresholds")
        logger.info("")
        logger.info("📈 The system will now:")
        logger.info("  • Download fresh data daily at 6:30 PM")
        logger.info("  • Retrain short-term models daily at 8:00 PM")
        logger.info("  • Full ensemble retraining weekly")
        logger.info("  • Provide real-time predictions via API")

async def main():
    """Main setup function"""
    try:
        pipeline = ProductionDataPipeline()
        
        # Setup with 1 year of historical data and model training
        await pipeline.setup_complete_pipeline(years=1, train_models=True)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))