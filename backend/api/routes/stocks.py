# Comprehensive Stock Search API for NSE/BSE/MCX/Currency/Indices
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import re
import sqlite3
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stocks", tags=["stocks"])

class ComprehensiveStockSearchService:
    def __init__(self, db_path="trading_platform.db"):
        self.db_path = db_path
    
    def search_stocks(
        self, 
        query: str, 
        exchanges: List[str] = None,
        segments: List[str] = None,
        limit: int = 20,
        fo_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Comprehensive search across all trading symbols
        """
        if not query or len(query.strip()) < 1:
            return []
        
        # Sanitize query
        query = re.sub(r'[^\w\s]', '', query).strip().upper()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_conditions = []
            params = []
            
            # Search in symbol and company name
            search_condition = "(symbol LIKE ? OR company_name LIKE ?)"
            where_conditions.append(search_condition)
            params.extend([f"%{query}%", f"%{query}%"])
            
            # Filter by exchanges
            if exchanges:
                exchange_placeholders = ",".join(["?" for _ in exchanges])
                where_conditions.append(f"exchange IN ({exchange_placeholders})")
                params.extend(exchanges)
            
            # Filter by segments
            if segments:
                segment_placeholders = ",".join(["?" for _ in segments])
                where_conditions.append(f"segment IN ({segment_placeholders})")
                params.extend(segments)
            
            # Filter by F&O enabled only
            if fo_only:
                where_conditions.append("is_fo_enabled = 1")
            
            # Only active symbols
            where_conditions.append("status = 'ACTIVE'")
            
            # Build final query with ranking
            where_clause = " AND ".join(where_conditions)
            
            sql_query = f"""
                SELECT 
                    s.symbol,
                    s.company_name,
                    s.exchange,
                    s.segment,
                    s.sector,
                    s.series,
                    s.market_cap,
                    s.lot_size,
                    s.tick_size,
                    s.is_fo_enabled,
                    s.is_etf,
                    s.is_index,
                    s.face_value,
                    sm.pe_ratio,
                    sm.pb_ratio,
                    sm.dividend_yield,
                    sm.beta,
                    CASE 
                        WHEN s.symbol = ? THEN 1
                        WHEN s.symbol LIKE ? THEN 2
                        WHEN s.company_name LIKE ? THEN 3
                        WHEN s.company_name LIKE ? THEN 4
                        ELSE 5
                    END as rank
                FROM stock_symbols s
                LEFT JOIN symbol_metadata sm ON s.symbol = sm.symbol
                WHERE {where_clause}
                ORDER BY rank ASC, s.market_cap DESC NULLS LAST, s.symbol ASC
                LIMIT ?
            """
            
            # Add ranking parameters
            ranking_params = [query, f"{query}%", f"{query}%", f"%{query}%"]
            final_params = ranking_params + params + [limit]
            
            cursor.execute(sql_query, final_params)
            results = cursor.fetchall()
            
            # Convert to dictionary format
            stocks = []
            for row in results:
                stock = {
                    "symbol": row[0],
                    "name": row[1],
                    "exchange": row[2],
                    "segment": row[3],
                    "sector": row[4] or "",
                    "series": row[5] or "",
                    "market_cap": row[6],
                    "lot_size": row[7],
                    "tick_size": row[8],
                    "is_fo_enabled": bool(row[9]),
                    "is_etf": bool(row[10]),
                    "is_index": bool(row[11]),
                    "face_value": row[12],
                    "pe_ratio": row[13],
                    "pb_ratio": row[14],
                    "dividend_yield": row[15],
                    "beta": row[16],
                }
                stocks.append(stock)
            
            conn.close()
            return stocks
            
        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            return []
    
    def get_popular_stocks(self, exchange: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular/most traded stocks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_condition = "status = 'ACTIVE'"
            params = []
            
            if exchange:
                where_condition += " AND exchange = ?"
                params.append(exchange)
            
            sql_query = f"""
                SELECT 
                    symbol, company_name, exchange, segment, sector, 
                    market_cap, is_fo_enabled, is_etf, is_index
                FROM stock_symbols 
                WHERE {where_condition}
                ORDER BY market_cap DESC NULLS LAST
                LIMIT ?
            """
            
            params.append(limit)
            cursor.execute(sql_query, params)
            results = cursor.fetchall()
            
            stocks = []
            for row in results:
                stock = {
                    "symbol": row[0],
                    "name": row[1],
                    "exchange": row[2],
                    "segment": row[3],
                    "sector": row[4] or "",
                    "market_cap": row[5],
                    "is_fo_enabled": bool(row[6]),
                    "is_etf": bool(row[7]),
                    "is_index": bool(row[8]),
                }
                stocks.append(stock)
            
            conn.close()
            return stocks
            
        except Exception as e:
            logger.error(f"Error getting popular stocks: {e}")
            return []
    
    def get_symbol_details(self, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM stock_symbols 
                WHERE symbol = ? AND exchange = ? AND status = 'ACTIVE'
            """, (symbol, exchange))
            
            result = cursor.fetchone()
            
            if result:
                # Get column names
                columns = [description[0] for description in cursor.description]
                stock_details = dict(zip(columns, result))
                
                conn.close()
                return stock_details
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error getting symbol details: {e}")
            return None
    
    def get_financial_data(self, symbol: str, exchange: str = None) -> Optional[Dict[str, Any]]:
        """Get comprehensive financial data for a symbol"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query both stock_symbols and symbol_metadata
            where_condition = "s.symbol = ?"
            params = [symbol]
            
            if exchange:
                where_condition += " AND s.exchange = ?"
                params.append(exchange)
            
            cursor.execute(f"""
                SELECT 
                    s.symbol,
                    s.company_name,
                    s.exchange,
                    s.segment,
                    s.sector,
                    s.market_cap,
                    s.face_value,
                    s.lot_size,
                    s.tick_size,
                    s.is_fo_enabled,
                    s.is_etf,
                    s.is_index,
                    sm.pe_ratio,
                    sm.pb_ratio,
                    sm.dividend_yield,
                    sm.beta,
                    sm.shares_outstanding,
                    sm.float_shares,
                    sm.avg_volume
                FROM stock_symbols s
                LEFT JOIN symbol_metadata sm ON s.symbol = sm.symbol
                WHERE {where_condition} AND s.status = 'ACTIVE'
                LIMIT 1
            """, params)
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return None
                
            financial_data = {
                "symbol": result[0],
                "company_name": result[1],
                "exchange": result[2],
                "segment": result[3],
                "sector": result[4],
                "market_cap": result[5],
                "face_value": result[6],
                "lot_size": result[7],
                "tick_size": result[8],
                "is_fo_enabled": bool(result[9]),
                "is_etf": bool(result[10]),
                "is_index": bool(result[11]),
                "pe_ratio": result[12],
                "pb_ratio": result[13],
                "dividend_yield": result[14],
                "beta": result[15],
                "shares_outstanding": result[16],
                "float_shares": result[17],
                "avg_volume": result[18],
                # Calculated fields
                "market_cap_category": self._get_market_cap_category(result[5]),
                "pe_rating": self._get_pe_rating(result[12]),
                "dividend_rating": self._get_dividend_rating(result[14]),
                "beta_rating": self._get_beta_rating(result[15])
            }
            
            return financial_data
            
        except Exception as e:
            logger.error(f"Error getting financial data for {symbol}: {e}")
            return None
    
    def _get_market_cap_category(self, market_cap):
        """Categorize market cap"""
        if not market_cap:
            return "Unknown"
        if market_cap >= 1000000:  # 10,000 Cr
            return "Large Cap"
        elif market_cap >= 50000:  # 500 Cr
            return "Mid Cap"
        elif market_cap >= 5000:   # 50 Cr
            return "Small Cap"
        else:
            return "Micro Cap"
    
    def _get_pe_rating(self, pe_ratio):
        """Get PE ratio rating"""
        if not pe_ratio:
            return "No PE Data"
        if pe_ratio < 15:
            return "Undervalued"
        elif pe_ratio < 25:
            return "Fair Value"
        else:
            return "Overvalued"
    
    def _get_dividend_rating(self, dividend_yield):
        """Get dividend yield rating"""
        if not dividend_yield:
            return "No Dividend"
        if dividend_yield > 4:
            return "High Yield"
        elif dividend_yield > 2:
            return "Good Yield"
        else:
            return "Low Yield"
    
    def _get_beta_rating(self, beta):
        """Get beta risk rating"""
        if not beta:
            return "No Beta Data"
        if beta < 0.8:
            return "Low Volatility"
        elif beta > 1.5:
            return "High Volatility"
        else:
            return "Moderate Volatility"

# Initialize service
search_service = ComprehensiveStockSearchService()

@router.get("/search")
async def search_stocks(
    q: str = Query(..., description="Search query (symbol or company name)"),
    exchanges: Optional[str] = Query(None, description="Comma-separated exchanges (NSE,BSE,MCX)"),
    segments: Optional[str] = Query(None, description="Comma-separated segments (EQUITY,COMMODITY,CURRENCY,INDEX,ETF)"),
    fo_only: bool = Query(False, description="F&O enabled stocks only"),
    limit: int = Query(20, description="Maximum number of results")
):
    """
    Search for stocks across all exchanges and segments
    
    Supports:
    - NSE & BSE Equity stocks
    - F&O enabled securities  
    - MCX Commodities (Gold, Silver, Crude Oil, etc.)
    - Currency derivatives (USD-INR, EUR-INR, etc.)
    - Stock indices (NIFTY, SENSEX, etc.)
    - ETFs
    """
    
    exchange_list = None
    if exchanges:
        exchange_list = [ex.strip().upper() for ex in exchanges.split(",")]
    
    segment_list = None
    if segments:
        segment_list = [seg.strip().upper() for seg in segments.split(",")]
    
    results = search_service.search_stocks(
        query=q,
        exchanges=exchange_list,
        segments=segment_list,
        limit=min(limit, 50),  # Cap at 50 results
        fo_only=fo_only
    )
    
    return {
        "success": True,
        "count": len(results),
        "query": q,
        "results": results
    }

@router.get("/popular")
async def get_popular_stocks(
    exchange: Optional[str] = Query(None, description="Exchange filter (NSE,BSE,MCX)"),
    limit: int = Query(10, description="Number of results")
):
    """Get popular/most traded stocks by market cap"""
    
    results = search_service.get_popular_stocks(
        exchange=exchange.upper() if exchange else None,
        limit=min(limit, 20)
    )
    
    return {
        "success": True,
        "count": len(results),
        "results": results
    }

@router.get("/trending")
async def get_trending_stocks(
    segment: Optional[str] = Query(None, description="Segment filter"),
    limit: int = Query(10, description="Number of results")
):
    """Get trending stocks (mock implementation for now)"""
    
    # For now, return F&O stocks as trending
    results = search_service.search_stocks(
        query="",
        segments=[segment.upper()] if segment else None,
        limit=min(limit, 20),
        fo_only=True
    )
    
    # Get top by market cap as proxy for trending
    results = [r for r in results if r.get('market_cap')]
    results.sort(key=lambda x: x['market_cap'], reverse=True)
    
    return {
        "success": True,
        "count": len(results),
        "results": results[:limit]
    }

@router.get("/symbol/{symbol}")
async def get_symbol_details(
    symbol: str,
    exchange: str = Query(..., description="Exchange (NSE,BSE,MCX)")
):
    """Get detailed information about a specific symbol"""
    
    result = search_service.get_symbol_details(
        symbol=symbol.upper(),
        exchange=exchange.upper()
    )
    
    if not result:
        raise HTTPException(status_code=404, message=f"Symbol {symbol} not found on {exchange}")
    
    return {
        "success": True,
        "symbol": result
    }

@router.get("/segments")
async def get_segments():
    """Get all available trading segments"""
    return {
        "success": True,
        "segments": [
            {"code": "EQUITY", "name": "Equity Stocks", "description": "NSE & BSE stocks"},
            {"code": "COMMODITY", "name": "Commodities", "description": "MCX commodities (Gold, Silver, Crude Oil, etc.)"},
            {"code": "CURRENCY", "name": "Currency Derivatives", "description": "Currency pairs (USD-INR, EUR-INR, etc.)"},
            {"code": "INDEX", "name": "Indices", "description": "Stock market indices (NIFTY, SENSEX, etc.)"},
            {"code": "ETF", "name": "Exchange Traded Funds", "description": "ETFs and mutual fund units"}
        ]
    }

@router.get("/exchanges")
async def get_exchanges():
    """Get all available exchanges"""
    return {
        "success": True,
        "exchanges": [
            {"code": "NSE", "name": "National Stock Exchange", "country": "India"},
            {"code": "BSE", "name": "Bombay Stock Exchange", "country": "India"}, 
            {"code": "MCX", "name": "Multi Commodity Exchange", "country": "India"}
        ]
    }

@router.get("/stats")
async def get_database_stats():
    """Get comprehensive database statistics"""
    try:
        conn = sqlite3.connect(search_service.db_path)
        cursor = conn.cursor()
        
        # Total symbols
        cursor.execute("SELECT COUNT(*) FROM stock_symbols WHERE status = 'ACTIVE'")
        total = cursor.fetchone()[0]
        
        # By exchange
        cursor.execute("""
            SELECT exchange, COUNT(*) as count 
            FROM stock_symbols 
            WHERE status = 'ACTIVE' 
            GROUP BY exchange 
            ORDER BY count DESC
        """)
        by_exchange = [{"exchange": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # By segment
        cursor.execute("""
            SELECT segment, COUNT(*) as count 
            FROM stock_symbols 
            WHERE status = 'ACTIVE' 
            GROUP BY segment 
            ORDER BY count DESC
        """)
        by_segment = [{"segment": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # F&O count
        cursor.execute("SELECT COUNT(*) FROM stock_symbols WHERE is_fo_enabled = 1 AND status = 'ACTIVE'")
        fo_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "total_symbols": total,
                "fo_enabled": fo_count,
                "by_exchange": by_exchange,
                "by_segment": by_segment
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail="Error fetching database statistics")

@router.get("/financial/{symbol}")
async def get_financial_data(
    symbol: str,
    exchange: Optional[str] = Query(None, description="Exchange filter (NSE, BSE, MCX)")
):
    """
    Get comprehensive financial data for a stock symbol
    
    Returns PE ratio, dividend yield, beta, market cap, and other financial metrics
    """
    try:
        financial_data = search_service.get_financial_data(symbol.upper(), exchange)
        
        if not financial_data:
            raise HTTPException(status_code=404, detail=f"Financial data not found for {symbol}")
        
        return {
            "success": True,
            "symbol": symbol.upper(),
            "financial_data": financial_data,
            "timestamp": "2024-01-01T00:00:00Z"  # In production, this would be real timestamp
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financial data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching financial data")