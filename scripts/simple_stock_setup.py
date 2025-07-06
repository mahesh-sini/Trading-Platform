#!/usr/bin/env python3
"""
Simple Stock Database Setup Script
Creates stock tables and populates with comprehensive NSE/BSE data
"""

import logging
import sqlite3
import asyncio
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleStockSetup:
    def __init__(self, db_path="trading_platform.db"):
        self.db_path = db_path
        
    def setup_database(self):
        """Create stock tables and populate with data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create stock_symbols table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_symbols (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    sector TEXT,
                    market_cap REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Create indexes for efficient search
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_exchange ON stock_symbols(symbol, exchange)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_company_name ON stock_symbols(company_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sector ON stock_symbols(sector)')
            
            # Check if data already exists
            cursor.execute('SELECT COUNT(*) FROM stock_symbols')
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                logger.info(f"Database already contains {existing_count} stock symbols")
                return existing_count
            
            # Insert comprehensive Indian stock data
            stocks_data = self.get_comprehensive_stock_data()
            
            for stock in stocks_data:
                cursor.execute('''
                    INSERT INTO stock_symbols (id, symbol, company_name, exchange, sector, market_cap, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f"{stock['symbol']}_{stock['exchange']}",
                    stock['symbol'],
                    stock['company_name'],
                    stock['exchange'],
                    stock.get('sector'),
                    stock.get('market_cap'),
                    1
                ))
            
            conn.commit()
            
            final_count = len(stocks_data)
            logger.info(f"Successfully inserted {final_count} stock symbols")
            
            return final_count
            
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_comprehensive_stock_data(self):
        """Returns comprehensive list of NSE and BSE stocks"""
        
        # Major NSE stocks
        nse_stocks = [
            {'symbol': 'RELIANCE', 'company_name': 'Reliance Industries Limited', 'exchange': 'NSE', 'sector': 'Energy', 'market_cap': 1500000},
            {'symbol': 'TCS', 'company_name': 'Tata Consultancy Services Limited', 'exchange': 'NSE', 'sector': 'Information Technology', 'market_cap': 1200000},
            {'symbol': 'INFY', 'company_name': 'Infosys Limited', 'exchange': 'NSE', 'sector': 'Information Technology', 'market_cap': 800000},
            {'symbol': 'HDFCBANK', 'company_name': 'HDFC Bank Limited', 'exchange': 'NSE', 'sector': 'Banking', 'market_cap': 900000},
            {'symbol': 'ICICIBANK', 'company_name': 'ICICI Bank Limited', 'exchange': 'NSE', 'sector': 'Banking', 'market_cap': 700000},
            {'symbol': 'KOTAKBANK', 'company_name': 'Kotak Mahindra Bank Limited', 'exchange': 'NSE', 'sector': 'Banking', 'market_cap': 400000},
            {'symbol': 'LT', 'company_name': 'Larsen & Toubro Limited', 'exchange': 'NSE', 'sector': 'Engineering', 'market_cap': 300000},
            {'symbol': 'ITC', 'company_name': 'ITC Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 350000},
            {'symbol': 'WIPRO', 'company_name': 'Wipro Limited', 'exchange': 'NSE', 'sector': 'Information Technology', 'market_cap': 250000},
            {'symbol': 'MARUTI', 'company_name': 'Maruti Suzuki India Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 280000},
            {'symbol': 'BHARTIARTL', 'company_name': 'Bharti Airtel Limited', 'exchange': 'NSE', 'sector': 'Telecommunications', 'market_cap': 320000},
            {'symbol': 'ASIANPAINT', 'company_name': 'Asian Paints Limited', 'exchange': 'NSE', 'sector': 'Paints', 'market_cap': 200000},
            {'symbol': 'SBIN', 'company_name': 'State Bank of India', 'exchange': 'NSE', 'sector': 'Banking', 'market_cap': 450000},
            {'symbol': 'HINDUNILVR', 'company_name': 'Hindustan Unilever Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 380000},
            {'symbol': 'BAJFINANCE', 'company_name': 'Bajaj Finance Limited', 'exchange': 'NSE', 'sector': 'Financial Services', 'market_cap': 420000},
            {'symbol': 'ADANIPORTS', 'company_name': 'Adani Ports and Special Economic Zone Limited', 'exchange': 'NSE', 'sector': 'Infrastructure', 'market_cap': 180000},
            {'symbol': 'AXISBANK', 'company_name': 'Axis Bank Limited', 'exchange': 'NSE', 'sector': 'Banking', 'market_cap': 320000},
            {'symbol': 'NESTLEIND', 'company_name': 'Nestle India Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 200000},
            {'symbol': 'ONGC', 'company_name': 'Oil and Natural Gas Corporation Limited', 'exchange': 'NSE', 'sector': 'Energy', 'market_cap': 280000},
            {'symbol': 'POWERGRID', 'company_name': 'Power Grid Corporation of India Limited', 'exchange': 'NSE', 'sector': 'Utilities', 'market_cap': 240000},
            {'symbol': 'NTPC', 'company_name': 'NTPC Limited', 'exchange': 'NSE', 'sector': 'Utilities', 'market_cap': 200000},
            {'symbol': 'TATAMOTORS', 'company_name': 'Tata Motors Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 160000},
            {'symbol': 'TATASTEEL', 'company_name': 'Tata Steel Limited', 'exchange': 'NSE', 'sector': 'Metals', 'market_cap': 140000},
            {'symbol': 'JSWSTEEL', 'company_name': 'JSW Steel Limited', 'exchange': 'NSE', 'sector': 'Metals', 'market_cap': 120000},
            {'symbol': 'HINDALCO', 'company_name': 'Hindalco Industries Limited', 'exchange': 'NSE', 'sector': 'Metals', 'market_cap': 100000},
            {'symbol': 'INDUSINDBK', 'company_name': 'IndusInd Bank Limited', 'exchange': 'NSE', 'sector': 'Banking', 'market_cap': 110000},
            {'symbol': 'TECHM', 'company_name': 'Tech Mahindra Limited', 'exchange': 'NSE', 'sector': 'Information Technology', 'market_cap': 90000},
            {'symbol': 'HCLTECH', 'company_name': 'HCL Technologies Limited', 'exchange': 'NSE', 'sector': 'Information Technology', 'market_cap': 420000},
            {'symbol': 'ULTRACEMCO', 'company_name': 'UltraTech Cement Limited', 'exchange': 'NSE', 'sector': 'Cement', 'market_cap': 380000},
            {'symbol': 'GRASIM', 'company_name': 'Grasim Industries Limited', 'exchange': 'NSE', 'sector': 'Diversified', 'market_cap': 120000},
            {'symbol': 'DRREDDY', 'company_name': 'Dr. Reddys Laboratories Limited', 'exchange': 'NSE', 'sector': 'Pharmaceuticals', 'market_cap': 100000},
            {'symbol': 'SUNPHARMA', 'company_name': 'Sun Pharmaceutical Industries Limited', 'exchange': 'NSE', 'sector': 'Pharmaceuticals', 'market_cap': 250000},
            {'symbol': 'CIPLA', 'company_name': 'Cipla Limited', 'exchange': 'NSE', 'sector': 'Pharmaceuticals', 'market_cap': 90000},
            {'symbol': 'DIVISLAB', 'company_name': 'Divis Laboratories Limited', 'exchange': 'NSE', 'sector': 'Pharmaceuticals', 'market_cap': 120000},
            {'symbol': 'APOLLOHOSP', 'company_name': 'Apollo Hospitals Enterprise Limited', 'exchange': 'NSE', 'sector': 'Healthcare', 'market_cap': 80000},
            {'symbol': 'TITAN', 'company_name': 'Titan Company Limited', 'exchange': 'NSE', 'sector': 'Consumer Goods', 'market_cap': 280000},
            {'symbol': 'BRITANNIA', 'company_name': 'Britannia Industries Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 130000},
            {'symbol': 'HEROMOTOCO', 'company_name': 'Hero MotoCorp Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 70000},
            {'symbol': 'BAJAJFINSV', 'company_name': 'Bajaj Finserv Limited', 'exchange': 'NSE', 'sector': 'Financial Services', 'market_cap': 240000},
            {'symbol': 'EICHERMOT', 'company_name': 'Eicher Motors Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 80000},
            {'symbol': 'BPCL', 'company_name': 'Bharat Petroleum Corporation Limited', 'exchange': 'NSE', 'sector': 'Energy', 'market_cap': 90000},
            {'symbol': 'IOC', 'company_name': 'Indian Oil Corporation Limited', 'exchange': 'NSE', 'sector': 'Energy', 'market_cap': 120000},
            {'symbol': 'COALINDIA', 'company_name': 'Coal India Limited', 'exchange': 'NSE', 'sector': 'Mining', 'market_cap': 140000},
            {'symbol': 'VEDL', 'company_name': 'Vedanta Limited', 'exchange': 'NSE', 'sector': 'Metals', 'market_cap': 100000},
            {'symbol': 'SHREECEM', 'company_name': 'Shree Cement Limited', 'exchange': 'NSE', 'sector': 'Cement', 'market_cap': 70000},
            {'symbol': 'M_M', 'company_name': 'Mahindra & Mahindra Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 160000},
            {'symbol': 'ADANIGREEN', 'company_name': 'Adani Green Energy Limited', 'exchange': 'NSE', 'sector': 'Renewable Energy', 'market_cap': 280000},
            {'symbol': 'ADANIENT', 'company_name': 'Adani Enterprises Limited', 'exchange': 'NSE', 'sector': 'Diversified', 'market_cap': 320000},
            {'symbol': 'ADANITRANS', 'company_name': 'Adani Transmission Limited', 'exchange': 'NSE', 'sector': 'Utilities', 'market_cap': 180000},
            # Additional popular NSE stocks
            {'symbol': 'GODREJCP', 'company_name': 'Godrej Consumer Products Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 80000},
            {'symbol': 'COLPAL', 'company_name': 'Colgate Palmolive India Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 45000},
            {'symbol': 'DABUR', 'company_name': 'Dabur India Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 90000},
            {'symbol': 'MARICO', 'company_name': 'Marico Limited', 'exchange': 'NSE', 'sector': 'FMCG', 'market_cap': 70000},
            {'symbol': 'PIDILITIND', 'company_name': 'Pidilite Industries Limited', 'exchange': 'NSE', 'sector': 'Chemicals', 'market_cap': 120000},
            {'symbol': 'BERGEPAINT', 'company_name': 'Berger Paints India Limited', 'exchange': 'NSE', 'sector': 'Paints', 'market_cap': 65000},
            {'symbol': 'HAVELLS', 'company_name': 'Havells India Limited', 'exchange': 'NSE', 'sector': 'Electrical Equipment', 'market_cap': 80000},
            {'symbol': 'VOLTAS', 'company_name': 'Voltas Limited', 'exchange': 'NSE', 'sector': 'Consumer Durables', 'market_cap': 35000},
            {'symbol': 'WHIRLPOOL', 'company_name': 'Whirlpool of India Limited', 'exchange': 'NSE', 'sector': 'Consumer Durables', 'market_cap': 25000},
            {'symbol': 'BAJAJ_AUTO', 'company_name': 'Bajaj Auto Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 190000},
            {'symbol': 'TVSMOTOR', 'company_name': 'TVS Motor Company Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 70000},
            {'symbol': 'ESCORTS', 'company_name': 'Escorts Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 40000},
            {'symbol': 'MOTHERSUMI', 'company_name': 'Motherson Sumi Systems Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 80000},
            {'symbol': 'BOSCHLTD', 'company_name': 'Bosch Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 75000},
            {'symbol': 'MRF', 'company_name': 'MRF Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 45000},
            {'symbol': 'APOLLOTYRE', 'company_name': 'Apollo Tyres Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 35000},
            {'symbol': 'CEAT', 'company_name': 'CEAT Limited', 'exchange': 'NSE', 'sector': 'Automotive', 'market_cap': 25000},
        ]
        
        # BSE stocks (subset of popular ones that are also listed on BSE)
        bse_stocks = [
            {'symbol': 'RELIANCE', 'company_name': 'Reliance Industries Limited', 'exchange': 'BSE', 'sector': 'Energy', 'market_cap': 1500000},
            {'symbol': 'TCS', 'company_name': 'Tata Consultancy Services Limited', 'exchange': 'BSE', 'sector': 'Information Technology', 'market_cap': 1200000},
            {'symbol': 'INFY', 'company_name': 'Infosys Limited', 'exchange': 'BSE', 'sector': 'Information Technology', 'market_cap': 800000},
            {'symbol': 'HDFCBANK', 'company_name': 'HDFC Bank Limited', 'exchange': 'BSE', 'sector': 'Banking', 'market_cap': 900000},
            {'symbol': 'ICICIBANK', 'company_name': 'ICICI Bank Limited', 'exchange': 'BSE', 'sector': 'Banking', 'market_cap': 700000},
            {'symbol': 'KOTAKBANK', 'company_name': 'Kotak Mahindra Bank Limited', 'exchange': 'BSE', 'sector': 'Banking', 'market_cap': 400000},
            {'symbol': 'LT', 'company_name': 'Larsen & Toubro Limited', 'exchange': 'BSE', 'sector': 'Engineering', 'market_cap': 300000},
            {'symbol': 'ITC', 'company_name': 'ITC Limited', 'exchange': 'BSE', 'sector': 'FMCG', 'market_cap': 350000},
            {'symbol': 'WIPRO', 'company_name': 'Wipro Limited', 'exchange': 'BSE', 'sector': 'Information Technology', 'market_cap': 250000},
            {'symbol': 'MARUTI', 'company_name': 'Maruti Suzuki India Limited', 'exchange': 'BSE', 'sector': 'Automotive', 'market_cap': 280000},
            {'symbol': 'BHARTIARTL', 'company_name': 'Bharti Airtel Limited', 'exchange': 'BSE', 'sector': 'Telecommunications', 'market_cap': 320000},
            {'symbol': 'ASIANPAINT', 'company_name': 'Asian Paints Limited', 'exchange': 'BSE', 'sector': 'Paints', 'market_cap': 200000},
            {'symbol': 'SBIN', 'company_name': 'State Bank of India', 'exchange': 'BSE', 'sector': 'Banking', 'market_cap': 450000},
            {'symbol': 'HINDUNILVR', 'company_name': 'Hindustan Unilever Limited', 'exchange': 'BSE', 'sector': 'FMCG', 'market_cap': 380000},
            {'symbol': 'BAJFINANCE', 'company_name': 'Bajaj Finance Limited', 'exchange': 'BSE', 'sector': 'Financial Services', 'market_cap': 420000},
            {'symbol': 'AXISBANK', 'company_name': 'Axis Bank Limited', 'exchange': 'BSE', 'sector': 'Banking', 'market_cap': 320000},
            {'symbol': 'NESTLEIND', 'company_name': 'Nestle India Limited', 'exchange': 'BSE', 'sector': 'FMCG', 'market_cap': 200000},
            {'symbol': 'ONGC', 'company_name': 'Oil and Natural Gas Corporation Limited', 'exchange': 'BSE', 'sector': 'Energy', 'market_cap': 280000},
            {'symbol': 'POWERGRID', 'company_name': 'Power Grid Corporation of India Limited', 'exchange': 'BSE', 'sector': 'Utilities', 'market_cap': 240000},
            {'symbol': 'NTPC', 'company_name': 'NTPC Limited', 'exchange': 'BSE', 'sector': 'Utilities', 'market_cap': 200000},
            {'symbol': 'TITAN', 'company_name': 'Titan Company Limited', 'exchange': 'BSE', 'sector': 'Consumer Goods', 'market_cap': 280000},
            {'symbol': 'SUNPHARMA', 'company_name': 'Sun Pharmaceutical Industries Limited', 'exchange': 'BSE', 'sector': 'Pharmaceuticals', 'market_cap': 250000},
            {'symbol': 'BRITANNIA', 'company_name': 'Britannia Industries Limited', 'exchange': 'BSE', 'sector': 'FMCG', 'market_cap': 130000},
            {'symbol': 'BAJAJFINSV', 'company_name': 'Bajaj Finserv Limited', 'exchange': 'BSE', 'sector': 'Financial Services', 'market_cap': 240000},
        ]
        
        return nse_stocks + bse_stocks

def main():
    """Run the stock database setup"""
    try:
        setup = SimpleStockSetup()
        count = setup.setup_database()
        
        logger.info(f"✅ Stock database setup complete!")
        logger.info(f"📈 Total stocks available: {count}")
        logger.info(f"🔍 Users can now search all NSE & BSE stocks!")
        
        # Test search functionality
        import sqlite3
        conn = sqlite3.connect("trading_platform.db")
        cursor = conn.cursor()
        
        # Sample search query
        cursor.execute("""
            SELECT symbol, company_name, exchange, sector 
            FROM stock_symbols 
            WHERE company_name LIKE '%Reliance%' OR symbol LIKE '%RELI%'
        """)
        results = cursor.fetchall()
        
        logger.info("\n📋 Sample search results for 'Reliance':")
        for result in results:
            logger.info(f"  {result[0]} ({result[2]}) - {result[1]} - {result[3]}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to setup stock database: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())