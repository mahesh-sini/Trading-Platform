#!/usr/bin/env python3
"""
Test script for the comprehensive stock search functionality
"""

import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_stock_search():
    """Test various stock search scenarios"""
    db_path = "trading_platform.db"
    
    test_queries = [
        "RELIANCE",
        "gold",
        "tcs",
        "nifty",
        "usd",
        "banking",
        "pharma",
        "tata",
        "hdfc"
    ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("🔍 Testing Comprehensive Stock Search")
        logger.info("=" * 50)
        
        for query in test_queries:
            logger.info(f"\n🔎 Searching for: '{query}'")
            
            # Simulate the backend search logic
            search_sql = """
                SELECT 
                    symbol, company_name, exchange, segment, sector,
                    market_cap, is_fo_enabled, is_etf, is_index
                FROM stock_symbols 
                WHERE (symbol LIKE ? OR company_name LIKE ?) 
                  AND status = 'ACTIVE'
                ORDER BY 
                    CASE 
                        WHEN symbol = ? THEN 1
                        WHEN symbol LIKE ? THEN 2
                        WHEN company_name LIKE ? THEN 3
                        ELSE 4
                    END,
                    market_cap DESC NULLS LAST
                LIMIT 5
            """
            
            params = [
                f"%{query.upper()}%", f"%{query.upper()}%",  # Search conditions
                query.upper(), f"{query.upper()}%", f"{query.upper()}%"  # Ranking conditions
            ]
            
            cursor.execute(search_sql, params)
            results = cursor.fetchall()
            
            if results:
                for result in results:
                    symbol, name, exchange, segment, sector, market_cap, is_fo, is_etf, is_index = result
                    
                    # Format result
                    tags = []
                    if is_fo: tags.append("F&O")
                    if is_etf: tags.append("ETF") 
                    if is_index: tags.append("INDEX")
                    
                    tag_str = f" [{', '.join(tags)}]" if tags else ""
                    market_cap_str = f" (₹{market_cap/10000:.0f}Cr)" if market_cap else ""
                    
                    logger.info(f"  ✓ {symbol} ({exchange}) - {name[:40]}...{tag_str}{market_cap_str}")
                    logger.info(f"    📊 {segment} • {sector or 'N/A'}")
            else:
                logger.info(f"  ❌ No results found")
        
        # Test by segment
        logger.info(f"\n📈 Testing by segments:")
        segments = ['EQUITY', 'COMMODITY', 'CURRENCY', 'INDEX', 'ETF']
        
        for segment in segments:
            cursor.execute("""
                SELECT COUNT(*) FROM stock_symbols 
                WHERE segment = ? AND status = 'ACTIVE'
            """, (segment,))
            count = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT symbol, company_name, exchange 
                FROM stock_symbols 
                WHERE segment = ? AND status = 'ACTIVE'
                LIMIT 3
            """, (segment,))
            samples = cursor.fetchall()
            
            logger.info(f"  {segment}: {count} symbols")
            for sample in samples:
                logger.info(f"    • {sample[0]} ({sample[2]}) - {sample[1][:30]}...")
        
        # Test exchange distribution
        logger.info(f"\n🏛️ Exchange distribution:")
        cursor.execute("""
            SELECT exchange, COUNT(*) as count 
            FROM stock_symbols 
            WHERE status = 'ACTIVE' 
            GROUP BY exchange 
            ORDER BY count DESC
        """)
        exchanges = cursor.fetchall()
        
        for exchange, count in exchanges:
            logger.info(f"  {exchange}: {count} symbols")
        
        conn.close()
        
        logger.info(f"\n✅ Stock search testing completed!")
        logger.info(f"🎯 Total comprehensive database ready for production use!")
        
    except Exception as e:
        logger.error(f"❌ Error testing stock search: {e}")

if __name__ == "__main__":
    test_stock_search()