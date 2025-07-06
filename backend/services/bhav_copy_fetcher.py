"""
NSE/BSE Bhav Copy Fetcher
Downloads and processes official daily market data from NSE and BSE
"""

import asyncio
import aiohttp
import pandas as pd
import sqlite3
import logging
import zipfile
import io
import csv
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import requests
from pathlib import Path
import os
import shutil
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

@dataclass
class BhavDataPoint:
    symbol: str
    exchange: str
    date: str
    open: float
    high: float
    low: float
    close: float
    last: float
    prev_close: float
    total_traded_qty: int
    total_traded_value: float
    series: str
    isin: str
    source: str

class BhavCopyFetcher:
    """
    Official NSE and BSE Bhav Copy fetcher
    Downloads daily market data from exchange websites
    """
    
    def __init__(self, db_path="trading_platform.db", data_dir="data/bhav_copies"):
        self.db_path = db_path
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # NSE URLs (as of 2024)
        self.nse_base_url = "https://nsearchives.nseindia.com/content/historical/EQUITIES"
        self.nse_bhav_url = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv"
        
        # BSE URLs (as of 2024) 
        self.bse_base_url = "https://www.bseindia.com/download/BhavCopy/Equity"
        self.bse_bhav_url = "https://www.bseindia.com/download/BhavCopy/Equity/EQ{date_bse}_CSV.ZIP"
        
        # Headers to mimic browser requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def setup_bhav_data_table(self):
        """Create table for storing bhav copy data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bhav_data (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    date DATE NOT NULL,
                    series TEXT,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    last REAL,
                    prev_close REAL,
                    total_traded_qty INTEGER,
                    total_traded_value REAL,
                    isin TEXT,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, exchange, date, series)
                )
            ''')
            
            # Create indexes for efficient queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bhav_symbol_date ON bhav_data(symbol, exchange, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bhav_date ON bhav_data(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bhav_symbol ON bhav_data(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bhav_exchange ON bhav_data(exchange)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_bhav_series ON bhav_data(series)')
            
            conn.commit()
            logger.info("Bhav data table created successfully")
            
        except Exception as e:
            logger.error(f"Error creating bhav data table: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_trading_date(self, target_date: date) -> Optional[date]:
        """Get the last trading date before or on target_date (excludes weekends/holidays)"""
        # Simple weekend exclusion (more sophisticated holiday calendar needed for production)
        while target_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            target_date -= timedelta(days=1)
        return target_date
    
    async def download_nse_bhav_copy(self, trade_date: date) -> Optional[Path]:
        """Download NSE bhav copy for given date"""
        try:
            # Format date for NSE (ddMMyyyy)
            date_str = trade_date.strftime("%d%m%Y")
            
            # Try multiple URL formats as NSE changes formats occasionally
            urls_to_try = [
                f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv",
                f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{trade_date.year}/{trade_date.strftime('%b').upper()}/cm{date_str}bhav.csv.zip",
                f"https://www1.nseindia.com/content/historical/EQUITIES/{trade_date.year}/{trade_date.strftime('%b').upper()}/cm{date_str}bhav.csv.zip"
            ]
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                for url in urls_to_try:
                    try:
                        logger.info(f"Trying NSE URL: {url}")
                        async with session.get(url) as response:
                            if response.status == 200:
                                content = await response.read()
                                
                                # Save file
                                filename = f"nse_bhav_{date_str}.csv"
                                if url.endswith('.zip'):
                                    filename = f"nse_bhav_{date_str}.zip"
                                
                                file_path = self.data_dir / filename
                                
                                with open(file_path, 'wb') as f:
                                    f.write(content)
                                
                                # Extract if zip file
                                if filename.endswith('.zip'):
                                    csv_path = self.extract_zip_file(file_path, f"nse_bhav_{date_str}.csv")
                                    if csv_path:
                                        return csv_path
                                else:
                                    return file_path
                                    
                    except Exception as e:
                        logger.warning(f"Failed to download from {url}: {e}")
                        continue
            
            logger.error(f"Failed to download NSE bhav copy for {trade_date}")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading NSE bhav copy: {e}")
            return None
    
    async def download_bse_bhav_copy(self, trade_date: date) -> Optional[Path]:
        """Download BSE bhav copy for given date"""
        try:
            # Format date for BSE (ddmmyy)
            date_str = trade_date.strftime("%d%m%y")
            
            url = f"https://www.bseindia.com/download/BhavCopy/Equity/EQ{date_str}_CSV.ZIP"
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                try:
                    logger.info(f"Downloading BSE bhav copy from: {url}")
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            
                            # Save zip file
                            zip_path = self.data_dir / f"bse_bhav_{date_str}.zip"
                            with open(zip_path, 'wb') as f:
                                f.write(content)
                            
                            # Extract CSV
                            csv_path = self.extract_zip_file(zip_path, f"bse_bhav_{date_str}.csv")
                            return csv_path
                        else:
                            logger.error(f"BSE download failed with status: {response.status}")
                            return None
                            
                except Exception as e:
                    logger.error(f"Error downloading BSE bhav copy: {e}")
                    return None
            
        except Exception as e:
            logger.error(f"Error in BSE bhav copy download: {e}")
            return None
    
    def extract_zip_file(self, zip_path: Path, output_name: str) -> Optional[Path]:
        """Extract CSV file from zip archive"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the first CSV file in the archive
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                if not csv_files:
                    logger.error(f"No CSV file found in {zip_path}")
                    return None
                
                # Extract the first CSV file
                csv_filename = csv_files[0]
                zip_ref.extract(csv_filename, self.data_dir)
                
                # Rename to our convention
                extracted_path = self.data_dir / csv_filename
                output_path = self.data_dir / output_name
                
                if extracted_path.exists():
                    shutil.move(str(extracted_path), str(output_path))
                    logger.info(f"Extracted and renamed to {output_path}")
                    return output_path
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting zip file {zip_path}: {e}")
            return None
    
    def parse_nse_bhav_csv(self, file_path: Path, trade_date: date) -> List[BhavDataPoint]:
        """Parse NSE bhav copy CSV file"""
        try:
            logger.info(f"Parsing NSE bhav copy: {file_path}")
            
            # NSE CSV columns (may vary by date, handle flexibly)
            df = pd.read_csv(file_path)
            
            # Standardize column names (NSE uses different formats)
            column_mapping = {
                'SYMBOL': 'symbol',
                'SERIES': 'series', 
                'OPEN': 'open',
                'HIGH': 'high',
                'LOW': 'low',
                'CLOSE': 'close',
                'LAST': 'last',
                'PREVCLOSE': 'prev_close',
                'TOTTRDQTY': 'total_traded_qty',
                'TOTTRDVAL': 'total_traded_value',
                'ISIN': 'isin'
            }
            
            # Rename columns if they exist
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Filter for equity series (EQ, BE, etc.)
            if 'series' in df.columns:
                df = df[df['series'].isin(['EQ', 'BE', 'BZ', 'BL'])]
            
            data_points = []
            for _, row in df.iterrows():
                try:
                    data_point = BhavDataPoint(
                        symbol=str(row.get('symbol', '')).strip(),
                        exchange='NSE',
                        date=trade_date.strftime('%Y-%m-%d'),
                        open=float(row.get('open', 0)),
                        high=float(row.get('high', 0)),
                        low=float(row.get('low', 0)),
                        close=float(row.get('close', 0)),
                        last=float(row.get('last', row.get('close', 0))),
                        prev_close=float(row.get('prev_close', 0)),
                        total_traded_qty=int(row.get('total_traded_qty', 0)),
                        total_traded_value=float(row.get('total_traded_value', 0)),
                        series=str(row.get('series', 'EQ')),
                        isin=str(row.get('isin', '')),
                        source='nse_bhav'
                    )
                    
                    # Basic validation
                    if data_point.symbol and data_point.close > 0:
                        data_points.append(data_point)
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing NSE row: {e}")
                    continue
            
            logger.info(f"Parsed {len(data_points)} NSE records")
            return data_points
            
        except Exception as e:
            logger.error(f"Error parsing NSE bhav CSV: {e}")
            return []
    
    def parse_bse_bhav_csv(self, file_path: Path, trade_date: date) -> List[BhavDataPoint]:
        """Parse BSE bhav copy CSV file"""
        try:
            logger.info(f"Parsing BSE bhav copy: {file_path}")
            
            # BSE CSV format
            df = pd.read_csv(file_path)
            
            # BSE column mapping
            column_mapping = {
                'SC_CODE': 'symbol',
                'SC_NAME': 'name',
                'SC_GROUP': 'series',
                'SC_TYPE': 'type',
                'OPEN': 'open',
                'HIGH': 'high', 
                'LOW': 'low',
                'CLOSE': 'close',
                'LAST': 'last',
                'PREVCLOSE': 'prev_close',
                'NO_TRADES': 'trades',
                'NO_OF_SHRS': 'total_traded_qty',
                'NET_TURNOV': 'total_traded_value',
                'ISIN_CODE': 'isin'
            }
            
            # Rename columns
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Filter for equity shares
            if 'series' in df.columns:
                df = df[df['series'].isin(['A', 'B', 'T', 'XT'])]
            
            data_points = []
            for _, row in df.iterrows():
                try:
                    # BSE uses numeric codes, we need symbol names
                    symbol = str(row.get('name', row.get('symbol', ''))).strip()
                    
                    data_point = BhavDataPoint(
                        symbol=symbol,
                        exchange='BSE',
                        date=trade_date.strftime('%Y-%m-%d'),
                        open=float(row.get('open', 0)),
                        high=float(row.get('high', 0)),
                        low=float(row.get('low', 0)),
                        close=float(row.get('close', 0)),
                        last=float(row.get('last', row.get('close', 0))),
                        prev_close=float(row.get('prev_close', 0)),
                        total_traded_qty=int(row.get('total_traded_qty', 0)),
                        total_traded_value=float(row.get('total_traded_value', 0)),
                        series=str(row.get('series', 'A')),
                        isin=str(row.get('isin', '')),
                        source='bse_bhav'
                    )
                    
                    # Basic validation
                    if data_point.symbol and data_point.close > 0:
                        data_points.append(data_point)
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing BSE row: {e}")
                    continue
            
            logger.info(f"Parsed {len(data_points)} BSE records")
            return data_points
            
        except Exception as e:
            logger.error(f"Error parsing BSE bhav CSV: {e}")
            return []
    
    def store_bhav_data(self, data_points: List[BhavDataPoint]) -> int:
        """Store bhav data points in database"""
        if not data_points:
            return 0
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            stored_count = 0
            for point in data_points:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO bhav_data (
                            id, symbol, exchange, date, series, open, high, low, close,
                            last, prev_close, total_traded_qty, total_traded_value, 
                            isin, source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f"{point.symbol}_{point.exchange}_{point.date}_{point.series}",
                        point.symbol,
                        point.exchange,
                        point.date,
                        point.series,
                        point.open,
                        point.high,
                        point.low,
                        point.close,
                        point.last,
                        point.prev_close,
                        point.total_traded_qty,
                        point.total_traded_value,
                        point.isin,
                        point.source
                    ))
                    stored_count += 1
                except sqlite3.IntegrityError:
                    # Data already exists
                    continue
            
            conn.commit()
            logger.info(f"Stored {stored_count} bhav data points")
            return stored_count
            
        except Exception as e:
            logger.error(f"Error storing bhav data: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    async def download_bhav_data(self, trade_date: Optional[date] = None) -> Dict[str, Any]:
        """Download and process bhav copy data for a specific date"""
        if trade_date is None:
            trade_date = self.get_trading_date(date.today() - timedelta(days=1))
        
        logger.info(f"🚀 Starting bhav copy download for {trade_date}")
        
        results = {
            "date": trade_date.strftime('%Y-%m-%d'),
            "nse": {"success": False, "records": 0, "file": None},
            "bse": {"success": False, "records": 0, "file": None},
            "total_records": 0,
            "errors": []
        }
        
        # Setup database
        self.setup_bhav_data_table()
        
        # Download NSE data
        try:
            nse_file = await self.download_nse_bhav_copy(trade_date)
            if nse_file and nse_file.exists():
                nse_data = self.parse_nse_bhav_csv(nse_file, trade_date)
                if nse_data:
                    stored = self.store_bhav_data(nse_data)
                    results["nse"] = {
                        "success": True,
                        "records": stored,
                        "file": str(nse_file)
                    }
                    results["total_records"] += stored
                    logger.info(f"✅ NSE: Downloaded and stored {stored} records")
                else:
                    results["errors"].append("NSE: Failed to parse data")
            else:
                results["errors"].append("NSE: Failed to download file")
        except Exception as e:
            error_msg = f"NSE: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        # Download BSE data
        try:
            bse_file = await self.download_bse_bhav_copy(trade_date)
            if bse_file and bse_file.exists():
                bse_data = self.parse_bse_bhav_csv(bse_file, trade_date)
                if bse_data:
                    stored = self.store_bhav_data(bse_data)
                    results["bse"] = {
                        "success": True,
                        "records": stored,
                        "file": str(bse_file)
                    }
                    results["total_records"] += stored
                    logger.info(f"✅ BSE: Downloaded and stored {stored} records")
                else:
                    results["errors"].append("BSE: Failed to parse data")
            else:
                results["errors"].append("BSE: Failed to download file")
        except Exception as e:
            error_msg = f"BSE: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        # Summary
        success_count = sum(1 for exchange in ["nse", "bse"] if results[exchange]["success"])
        logger.info(f"📊 Bhav copy download completed: {success_count}/2 exchanges successful")
        logger.info(f"📈 Total records stored: {results['total_records']}")
        
        if results["errors"]:
            logger.warning(f"⚠️ Errors encountered: {'; '.join(results['errors'])}")
        
        return results
    
    async def download_historical_bhav_data(self, start_date: date, end_date: Optional[date] = None) -> Dict[str, Any]:
        """Download historical bhav data for a date range"""
        if end_date is None:
            end_date = self.get_trading_date(date.today() - timedelta(days=1))
        
        logger.info(f"🚀 Starting historical bhav download: {start_date} to {end_date}")
        
        current_date = start_date
        total_stats = {
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "total_days": 0,
            "successful_days": 0,
            "total_records": 0,
            "nse_records": 0,
            "bse_records": 0,
            "errors": []
        }
        
        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                try:
                    logger.info(f"📅 Processing {current_date}")
                    total_stats["total_days"] += 1
                    
                    result = await self.download_bhav_data(current_date)
                    
                    if result["total_records"] > 0:
                        total_stats["successful_days"] += 1
                        total_stats["total_records"] += result["total_records"]
                        total_stats["nse_records"] += result["nse"]["records"]
                        total_stats["bse_records"] += result["bse"]["records"]
                    
                    if result["errors"]:
                        total_stats["errors"].extend([f"{current_date}: {err}" for err in result["errors"]])
                    
                    # Rate limiting between requests
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    error_msg = f"{current_date}: {str(e)}"
                    total_stats["errors"].append(error_msg)
                    logger.error(error_msg)
            
            current_date += timedelta(days=1)
        
        logger.info(f"✅ Historical download completed!")
        logger.info(f"📊 Stats: {total_stats['successful_days']}/{total_stats['total_days']} days successful")
        logger.info(f"📈 Total records: {total_stats['total_records']} (NSE: {total_stats['nse_records']}, BSE: {total_stats['bse_records']})")
        
        return total_stats
    
    def get_training_data_from_bhav(self, symbol: str, exchange: str, lookback_days: int = 252) -> pd.DataFrame:
        """Get training data from bhav copies"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            query = """
                SELECT date, open, high, low, close, total_traded_qty as volume, prev_close
                FROM bhav_data
                WHERE symbol = ? AND exchange = ? 
                AND date >= ? AND date <= ?
                AND series IN ('EQ', 'BE', 'A', 'B')
                ORDER BY date ASC
            """
            
            df = pd.read_sql_query(query, conn, params=(
                symbol, exchange, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
            ))
            
            if df.empty:
                logger.warning(f"No bhav data found for {symbol} ({exchange})")
                return pd.DataFrame()
            
            # Convert date column to datetime
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # Fill missing values
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            logger.info(f"Retrieved {len(df)} bhav data points for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting bhav training data for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

# Global instance
bhav_fetcher = BhavCopyFetcher()