#!/usr/bin/env python3
"""
Populate Financial Data for Comprehensive Stock Database
Adds realistic financial metrics (PE, dividend yield, beta, etc.) to symbols
"""

import sqlite3
import logging
import random
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinancialDataPopulator:
    def __init__(self, db_path="trading_platform.db"):
        self.db_path = db_path
        
    def setup_symbol_metadata_table(self):
        """Create symbol_metadata table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS symbol_metadata (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL UNIQUE,
                    company_name TEXT,
                    exchange TEXT,
                    sector TEXT,
                    industry TEXT,
                    security_type TEXT,
                    market_cap_category TEXT,
                    market_cap REAL,
                    shares_outstanding REAL,
                    float_shares REAL,
                    avg_volume INTEGER,
                    pe_ratio REAL,
                    pb_ratio REAL,
                    dividend_yield REAL,
                    beta REAL,
                    is_active BOOLEAN DEFAULT 1,
                    is_tradeable BOOLEAN DEFAULT 1,
                    is_marginable BOOLEAN DEFAULT 1,
                    is_shortable BOOLEAN DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for efficient queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_symbol ON symbol_metadata(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_exchange ON symbol_metadata(exchange)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_sector ON symbol_metadata(sector)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_pe ON symbol_metadata(pe_ratio)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_dividend ON symbol_metadata(dividend_yield)')
            
            conn.commit()
            logger.info("Symbol metadata table created successfully")
            
        except Exception as e:
            logger.error(f"Error creating symbol metadata table: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_financial_ranges_by_sector(self, sector, segment):
        """Get realistic financial metric ranges based on sector and segment"""
        
        # Base ranges for different segments
        base_ranges = {
            "EQUITY": {
                "pe_ratio": (8, 35),
                "pb_ratio": (0.5, 4.0),
                "dividend_yield": (0, 8),
                "beta": (0.3, 2.0)
            },
            "INDEX": {
                "pe_ratio": (15, 25),
                "pb_ratio": (1.5, 3.0),
                "dividend_yield": (1, 3),
                "beta": (0.8, 1.2)
            },
            "ETF": {
                "pe_ratio": (12, 22),
                "pb_ratio": (1.0, 2.5),
                "dividend_yield": (1, 4),
                "beta": (0.7, 1.3)
            },
            "COMMODITY": {
                "pe_ratio": (10, 20),
                "pb_ratio": (0.8, 2.0),
                "dividend_yield": (0, 2),
                "beta": (0.5, 2.5)
            },
            "CURRENCY": {
                "pe_ratio": (15, 18),
                "pb_ratio": (1.0, 1.5),
                "dividend_yield": (0, 1),
                "beta": (0.1, 0.5)
            }
        }
        
        # Sector-specific adjustments for equity
        sector_adjustments = {
            "Banking": {"pe_ratio": (6, 18), "dividend_yield": (2, 6)},
            "Information Technology": {"pe_ratio": (20, 40), "dividend_yield": (0, 3)},
            "FMCG": {"pe_ratio": (25, 50), "dividend_yield": (1, 4)},
            "Energy": {"pe_ratio": (5, 15), "dividend_yield": (3, 8)},
            "Pharmaceuticals": {"pe_ratio": (15, 35), "dividend_yield": (0, 3)},
            "Automotive": {"pe_ratio": (10, 25), "dividend_yield": (1, 5)},
            "Metals": {"pe_ratio": (5, 20), "dividend_yield": (2, 6)},
            "Utilities": {"pe_ratio": (12, 22), "dividend_yield": (3, 7)},
            "Financial Services": {"pe_ratio": (8, 20), "dividend_yield": (1, 5)},
            "Telecommunications": {"pe_ratio": (8, 18), "dividend_yield": (2, 6)},
            "Cement": {"pe_ratio": (10, 25), "dividend_yield": (1, 4)},
            "Paints": {"pe_ratio": (30, 60), "dividend_yield": (0, 2)},
            "Infrastructure": {"pe_ratio": (12, 30), "dividend_yield": (0, 3)},
            "Engineering": {"pe_ratio": (15, 35), "dividend_yield": (1, 4)}
        }
        
        ranges = base_ranges.get(segment, base_ranges["EQUITY"])
        
        # Apply sector adjustments for equity
        if segment == "EQUITY" and sector in sector_adjustments:
            sector_adj = sector_adjustments[sector]
            for key, value in sector_adj.items():
                ranges[key] = value
        
        return ranges
    
    def generate_realistic_financials(self, symbol, company_name, exchange, segment, sector, market_cap):
        """Generate realistic financial metrics for a symbol"""
        
        ranges = self.get_financial_ranges_by_sector(sector, segment)
        
        # Generate PE ratio
        pe_min, pe_max = ranges["pe_ratio"]
        pe_ratio = round(random.uniform(pe_min, pe_max), 2) if random.random() > 0.1 else None
        
        # Generate PB ratio
        pb_min, pb_max = ranges["pb_ratio"]
        pb_ratio = round(random.uniform(pb_min, pb_max), 2) if random.random() > 0.05 else None
        
        # Generate dividend yield (some stocks don't pay dividends)
        div_min, div_max = ranges["dividend_yield"]
        dividend_yield = round(random.uniform(div_min, div_max), 2) if random.random() > 0.3 else None
        
        # Generate beta
        beta_min, beta_max = ranges["beta"]
        beta = round(random.uniform(beta_min, beta_max), 2) if random.random() > 0.05 else None
        
        # Generate shares outstanding based on market cap
        if market_cap:
            # Assume average price of 100-2000 for estimation
            avg_price = random.uniform(100, 2000)
            shares_outstanding = int((market_cap * 10000) / avg_price)  # market_cap in lakhs
            float_shares = int(shares_outstanding * random.uniform(0.7, 0.95))
        else:
            shares_outstanding = random.randint(10000000, 1000000000)
            float_shares = int(shares_outstanding * random.uniform(0.7, 0.95))
        
        # Generate average volume
        if market_cap and market_cap > 100000:  # Large caps have higher volume
            avg_volume = random.randint(500000, 5000000)
        elif market_cap and market_cap > 10000:  # Mid caps
            avg_volume = random.randint(50000, 1000000)
        else:  # Small caps
            avg_volume = random.randint(5000, 200000)
        
        # Market cap category
        if market_cap:
            if market_cap >= 1000000:
                market_cap_category = "Large Cap"
            elif market_cap >= 50000:
                market_cap_category = "Mid Cap"
            elif market_cap >= 5000:
                market_cap_category = "Small Cap"
            else:
                market_cap_category = "Micro Cap"
        else:
            market_cap_category = "Unknown"
        
        return {
            "symbol": symbol,
            "company_name": company_name,
            "exchange": exchange,
            "sector": sector,
            "security_type": segment.lower(),
            "market_cap_category": market_cap_category,
            "market_cap": market_cap,
            "shares_outstanding": shares_outstanding,
            "float_shares": float_shares,
            "avg_volume": avg_volume,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "dividend_yield": dividend_yield,
            "beta": beta,
            "is_active": True,
            "is_tradeable": True,
            "is_marginable": True,
            "is_shortable": True,
            "data_version": "1.0"
        }
    
    def populate_financial_data(self):
        """Populate financial data for all symbols"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all symbols from stock_symbols table
            cursor.execute("""
                SELECT symbol, company_name, exchange, segment, sector, market_cap
                FROM stock_symbols 
                WHERE status = 'ACTIVE'
                ORDER BY market_cap DESC NULLS LAST
            """)
            
            symbols = cursor.fetchall()
            logger.info(f"Found {len(symbols)} symbols to process")
            
            processed = 0
            for symbol_data in symbols:
                symbol, company_name, exchange, segment, sector, market_cap = symbol_data
                
                # Check if financial data already exists
                cursor.execute("SELECT symbol FROM symbol_metadata WHERE symbol = ?", (symbol,))
                if cursor.fetchone():
                    logger.debug(f"Skipping {symbol} - financial data already exists")
                    continue
                
                # Generate financial data
                financial_data = self.generate_realistic_financials(
                    symbol, company_name, exchange, segment, sector, market_cap
                )
                
                # Insert into symbol_metadata table
                cursor.execute("""
                    INSERT INTO symbol_metadata (
                        id, symbol, company_name, exchange, sector, security_type,
                        market_cap_category, market_cap, shares_outstanding, float_shares,
                        avg_volume, pe_ratio, pb_ratio, dividend_yield, beta,
                        is_active, is_tradeable, is_marginable, is_shortable, data_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"{symbol}_{exchange}",
                    financial_data["symbol"],
                    financial_data["company_name"], 
                    financial_data["exchange"],
                    financial_data["sector"],
                    financial_data["security_type"],
                    financial_data["market_cap_category"],
                    financial_data["market_cap"],
                    financial_data["shares_outstanding"],
                    financial_data["float_shares"],
                    financial_data["avg_volume"],
                    financial_data["pe_ratio"],
                    financial_data["pb_ratio"],
                    financial_data["dividend_yield"],
                    financial_data["beta"],
                    financial_data["is_active"],
                    financial_data["is_tradeable"],
                    financial_data["is_marginable"],
                    financial_data["is_shortable"],
                    financial_data["data_version"]
                ))
                
                processed += 1
                
                if processed % 10 == 0:
                    logger.info(f"Processed {processed}/{len(symbols)} symbols")
            
            conn.commit()
            logger.info(f"✅ Successfully populated financial data for {processed} symbols")
            
            # Show some statistics
            cursor.execute("SELECT COUNT(*) FROM symbol_metadata")
            total_financial = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM symbol_metadata WHERE pe_ratio IS NOT NULL")
            with_pe = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM symbol_metadata WHERE dividend_yield IS NOT NULL")
            with_dividend = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(pe_ratio) FROM symbol_metadata WHERE pe_ratio IS NOT NULL")
            avg_pe = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(dividend_yield) FROM symbol_metadata WHERE dividend_yield IS NOT NULL")
            avg_dividend = cursor.fetchone()[0]
            
            logger.info(f"📊 Financial Data Statistics:")
            logger.info(f"  Total symbols with financial data: {total_financial}")
            logger.info(f"  Symbols with PE ratio: {with_pe}")
            logger.info(f"  Symbols with dividend data: {with_dividend}")
            logger.info(f"  Average PE ratio: {avg_pe:.2f}" if avg_pe else "  Average PE ratio: N/A")
            logger.info(f"  Average dividend yield: {avg_dividend:.2f}%" if avg_dividend else "  Average dividend yield: N/A")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error populating financial data: {e}")
            return False

def main():
    """Main function to populate financial data"""
    try:
        populator = FinancialDataPopulator()
        
        logger.info("🚀 Starting Financial Data Population")
        logger.info("=" * 60)
        
        # Setup database table
        populator.setup_symbol_metadata_table()
        
        # Populate financial data
        success = populator.populate_financial_data()
        
        if success:
            logger.info("✅ Financial data population completed successfully!")
        else:
            logger.error("❌ Financial data population failed!")
            return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())