#!/usr/bin/env python3
"""
Stock Database Population Script
Fetches and populates all NSE & BSE stock symbols into the database
"""

import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.base import Base
from backend.models.market_data import StockSymbol
from backend.services.stock_data_fetcher import StockDataFetcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to populate stock database"""
    try:
        # Create database engine (use SQLite for local development)
        database_url = "sqlite:///./trading_platform.db"
        engine = create_engine(database_url, echo=False)
        
        # Create tables if they don't exist
        Base.metadata.create_all(engine)
        logger.info("Database tables created/verified")
        
        # Create session
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        try:
            # Initialize stock data fetcher
            fetcher = StockDataFetcher()
            
            # Populate database
            logger.info("Starting stock data population...")
            count = await fetcher.populate_database(db)
            
            logger.info(f"✅ Successfully populated database with {count} stock symbols")
            logger.info("Stock search functionality is now available!")
            
            # Display some sample data
            sample_stocks = db.query(StockSymbol).limit(10).all()
            logger.info("\nSample stocks in database:")
            for stock in sample_stocks:
                logger.info(f"  {stock.symbol} ({stock.exchange}) - {stock.company_name}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Error populating stock database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())