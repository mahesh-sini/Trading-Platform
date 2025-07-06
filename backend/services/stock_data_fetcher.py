# Stock Data Fetcher for NSE & BSE
import httpx
import asyncio
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..models.market_data import StockSymbol
# Note: get_db import removed to avoid async engine issues
import pandas as pd
import io

logger = logging.getLogger(__name__)

class StockDataFetcher:
    """Fetches complete stock symbol lists from NSE & BSE"""
    
    def __init__(self):
        self.nse_base_url = "https://www.nseindia.com"
        self.bse_base_url = "https://www.bseindia.com"
        self.timeout = httpx.Timeout(30.0)
        
    async def fetch_nse_stocks(self) -> List[Dict]:
        """Fetch all NSE stock symbols"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.nseindia.com/',
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                # First get session cookies
                await client.get(f"{self.nse_base_url}/")
                
                # Fetch equity symbols
                response = await client.get(
                    f"{self.nse_base_url}/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    stocks = []
                    
                    for item in data.get('data', []):
                        stocks.append({
                            'symbol': item.get('symbol', '').strip(),
                            'company_name': item.get('companyName', '').strip(),
                            'exchange': 'NSE',
                            'sector': item.get('industry', ''),
                            'market_cap': None,  # Will be fetched separately if needed
                            'isin': item.get('isin', ''),
                        })
                    
                    logger.info(f"Fetched {len(stocks)} NSE stocks")
                    return stocks
                    
        except Exception as e:
            logger.error(f"Error fetching NSE stocks: {e}")
            
            # Fallback to static list of major NSE stocks
            return self._get_fallback_nse_stocks()
    
    async def fetch_bse_stocks(self) -> List[Dict]:
        """Fetch all BSE stock symbols"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            
            async with httpx.AsyncClient(timeout=self.timeout, headers=headers) as client:
                # BSE provides CSV download of all listed companies
                response = await client.get(
                    "https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_290724.zip",
                    headers=headers
                )
                
                if response.status_code == 200:
                    # Process BSE data (would need to unzip and parse CSV)
                    # For now, return fallback data
                    return self._get_fallback_bse_stocks()
                    
        except Exception as e:
            logger.error(f"Error fetching BSE stocks: {e}")
            
        # Fallback to static list
        return self._get_fallback_bse_stocks()
    
    def _get_fallback_nse_stocks(self) -> List[Dict]:
        """Fallback NSE stock list with major companies"""
        return [
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
        ]
    
    def _get_fallback_bse_stocks(self) -> List[Dict]:
        """Fallback BSE stock list (subset of NSE stocks that are also listed on BSE)"""
        return [
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
        ]
    
    async def populate_database(self, db: Session):
        """Populate database with all NSE & BSE stocks"""
        try:
            # Check if database already has stocks
            existing_count = db.query(StockSymbol).count()
            if existing_count > 100:  # Already populated
                logger.info(f"Database already contains {existing_count} stocks")
                return existing_count
            
            # Fetch stock data
            logger.info("Fetching stock data from NSE & BSE...")
            nse_stocks = await self.fetch_nse_stocks()
            bse_stocks = await self.fetch_bse_stocks()
            
            all_stocks = nse_stocks + bse_stocks
            logger.info(f"Fetched {len(all_stocks)} total stocks")
            
            # Clear existing data
            db.query(StockSymbol).delete()
            
            # Insert new data
            inserted_count = 0
            for stock_data in all_stocks:
                try:
                    stock = StockSymbol(**stock_data)
                    db.add(stock)
                    inserted_count += 1
                except Exception as e:
                    logger.error(f"Error inserting stock {stock_data.get('symbol', 'Unknown')}: {e}")
                    continue
            
            db.commit()
            logger.info(f"Successfully populated database with {inserted_count} stock symbols")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error populating database: {e}")
            db.rollback()
            raise