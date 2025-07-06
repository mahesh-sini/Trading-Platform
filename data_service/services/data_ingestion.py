import asyncio
import logging
import pandas as pd
import yfinance as yf
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger(__name__)

class DataSource(Enum):
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    POLYGON = "polygon"
    FINNHUB = "finnhub"
    IEX_CLOUD = "iex_cloud"

@dataclass
class MarketDataPoint:
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    source: DataSource

@dataclass
class NewsItem:
    headline: str
    summary: str
    url: str
    source: str
    published_at: datetime
    symbols: List[str]
    sentiment_score: Optional[float] = None

class DataProvider:
    """Base class for data providers"""
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        raise NotImplementedError
    
    async def get_real_time_data(self, symbol: str) -> MarketDataPoint:
        raise NotImplementedError
    
    async def get_news(self, symbol: str = None, limit: int = 50) -> List[NewsItem]:
        raise NotImplementedError

class YahooFinanceProvider(DataProvider):
    def __init__(self):
        self.session = None
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return pd.DataFrame()
            
            # Standardize column names
            hist = hist.reset_index()
            hist.columns = [col.lower().replace(' ', '_') for col in hist.columns]
            hist['symbol'] = symbol
            hist['source'] = DataSource.YAHOO_FINANCE.value
            
            return hist
            
        except Exception as e:
            logger.error(f"Yahoo Finance historical data error for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    async def get_real_time_data(self, symbol: str) -> Optional[MarketDataPoint]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return None
            
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open_price=info.get('open', 0),
                high_price=info.get('dayHigh', 0),
                low_price=info.get('dayLow', 0),
                close_price=info.get('currentPrice', info.get('regularMarketPrice', 0)),
                volume=info.get('volume', 0),
                source=DataSource.YAHOO_FINANCE
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance real-time data error for {symbol}: {str(e)}")
            return None
    
    async def get_news(self, symbol: str = None, limit: int = 50) -> List[NewsItem]:
        try:
            if symbol:
                ticker = yf.Ticker(symbol)
                news_data = ticker.news
            else:
                # General market news - using a major index
                ticker = yf.Ticker("SPY")
                news_data = ticker.news
            
            news_items = []
            for item in news_data[:limit]:
                news_items.append(NewsItem(
                    headline=item.get('title', ''),
                    summary=item.get('summary', ''),
                    url=item.get('link', ''),
                    source=item.get('publisher', 'Yahoo Finance'),
                    published_at=datetime.fromtimestamp(item.get('providerPublishTime', 0)),
                    symbols=[symbol] if symbol else []
                ))
            
            return news_items
            
        except Exception as e:
            logger.error(f"Yahoo Finance news error: {str(e)}")
            return []

class AlphaVantageProvider(DataProvider):
    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"
    
    async def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")
            return pd.DataFrame()
        
        try:
            params = {
                'function': 'TIME_SERIES_DAILY',
                'symbol': symbol,
                'apikey': self.api_key,
                'outputsize': 'full'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()
            
            if 'Time Series (Daily)' not in data:
                logger.warning(f"No data returned from Alpha Vantage for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            time_series = data['Time Series (Daily)']
            df_data = []
            
            for date_str, values in time_series.items():
                df_data.append({
                    'date': pd.to_datetime(date_str),
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': int(values['5. volume']),
                    'symbol': symbol,
                    'source': DataSource.ALPHA_VANTAGE.value
                })
            
            df = pd.DataFrame(df_data)
            df = df.sort_values('date')
            
            # Filter by period
            if period == "1y":
                cutoff_date = datetime.now() - timedelta(days=365)
                df = df[df['date'] >= cutoff_date]
            
            return df
            
        except Exception as e:
            logger.error(f"Alpha Vantage historical data error for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    async def get_real_time_data(self, symbol: str) -> Optional[MarketDataPoint]:
        if not self.api_key:
            return None
        
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()
            
            if 'Global Quote' not in data:
                return None
            
            quote = data['Global Quote']
            
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(),
                open_price=float(quote['02. open']),
                high_price=float(quote['03. high']),
                low_price=float(quote['04. low']),
                close_price=float(quote['05. price']),
                volume=int(quote['06. volume']),
                source=DataSource.ALPHA_VANTAGE
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage real-time data error for {symbol}: {str(e)}")
            return None
    
    async def get_news(self, symbol: str = None, limit: int = 50) -> List[NewsItem]:
        if not self.api_key:
            return []
        
        try:
            params = {
                'function': 'NEWS_SENTIMENT',
                'apikey': self.api_key
            }
            
            if symbol:
                params['tickers'] = symbol
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()
            
            if 'feed' not in data:
                return []
            
            news_items = []
            for item in data['feed'][:limit]:
                news_items.append(NewsItem(
                    headline=item.get('title', ''),
                    summary=item.get('summary', ''),
                    url=item.get('url', ''),
                    source=item.get('source', ''),
                    published_at=datetime.strptime(item.get('time_published', ''), '%Y%m%dT%H%M%S'),
                    symbols=[ticker['ticker'] for ticker in item.get('ticker_sentiment', [])],
                    sentiment_score=float(item.get('overall_sentiment_score', 0))
                ))
            
            return news_items
            
        except Exception as e:
            logger.error(f"Alpha Vantage news error: {str(e)}")
            return []

class DataIngestionService:
    def __init__(self):
        self.providers = {
            DataSource.YAHOO_FINANCE: YahooFinanceProvider(),
            DataSource.ALPHA_VANTAGE: AlphaVantageProvider()
        }
        self.primary_provider = DataSource.YAHOO_FINANCE
        self.influx_client = None
        self.influx_write_api = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize the data ingestion service"""
        logger.info("Initializing Data Ingestion Service")
        
        # Initialize InfluxDB connection
        influx_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        influx_token = os.getenv("INFLUXDB_TOKEN")
        influx_org = os.getenv("INFLUXDB_ORG", "trading-platform")
        
        if influx_token:
            try:
                self.influx_client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
                self.influx_write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
                logger.info("InfluxDB connection established")
            except Exception as e:
                logger.warning(f"Failed to connect to InfluxDB: {str(e)}")
        
        self.is_running = True
        
    async def shutdown(self):
        """Shutdown the data ingestion service"""
        self.is_running = False
        if self.influx_client:
            self.influx_client.close()
        logger.info("Data Ingestion Service shutdown complete")
    
    async def get_historical_data(
        self, 
        symbol: str, 
        period: str = "1y",
        source: Optional[DataSource] = None
    ) -> pd.DataFrame:
        """Get historical market data for a symbol"""
        provider_source = source or self.primary_provider
        provider = self.providers.get(provider_source)
        
        if not provider:
            raise ValueError(f"Unsupported data source: {provider_source}")
        
        try:
            data = await provider.get_historical_data(symbol, period)
            
            # Store in InfluxDB if available
            if not data.empty and self.influx_write_api:
                await self._store_historical_data_influx(data)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {str(e)}")
            # Try fallback provider
            if provider_source != DataSource.YAHOO_FINANCE:
                logger.info(f"Trying fallback provider for {symbol}")
                fallback_provider = self.providers[DataSource.YAHOO_FINANCE]
                return await fallback_provider.get_historical_data(symbol, period)
            raise
    
    async def get_real_time_data(
        self, 
        symbol: str,
        source: Optional[DataSource] = None
    ) -> Optional[MarketDataPoint]:
        """Get real-time market data for a symbol"""
        provider_source = source or self.primary_provider
        provider = self.providers.get(provider_source)
        
        if not provider:
            raise ValueError(f"Unsupported data source: {provider_source}")
        
        try:
            data_point = await provider.get_real_time_data(symbol)
            
            # Store in InfluxDB if available
            if data_point and self.influx_write_api:
                await self._store_real_time_data_influx(data_point)
            
            return data_point
            
        except Exception as e:
            logger.error(f"Failed to get real-time data for {symbol}: {str(e)}")
            # Try fallback provider
            if provider_source != DataSource.YAHOO_FINANCE:
                logger.info(f"Trying fallback provider for {symbol}")
                fallback_provider = self.providers[DataSource.YAHOO_FINANCE]
                return await fallback_provider.get_real_time_data(symbol)
            raise
    
    async def get_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
        source: Optional[DataSource] = None
    ) -> List[NewsItem]:
        """Get news items"""
        provider_source = source or self.primary_provider
        provider = self.providers.get(provider_source)
        
        if not provider:
            raise ValueError(f"Unsupported data source: {provider_source}")
        
        try:
            return await provider.get_news(symbol, limit)
        except Exception as e:
            logger.error(f"Failed to get news: {str(e)}")
            raise
    
    async def _store_historical_data_influx(self, data: pd.DataFrame):
        """Store historical data in InfluxDB"""
        try:
            bucket = os.getenv("INFLUXDB_BUCKET", "market-data")
            
            points = []
            for _, row in data.iterrows():
                point = Point("market_data") \
                    .tag("symbol", row['symbol']) \
                    .tag("source", row['source']) \
                    .field("open", float(row['open'])) \
                    .field("high", float(row['high'])) \
                    .field("low", float(row['low'])) \
                    .field("close", float(row['close'])) \
                    .field("volume", int(row['volume'])) \
                    .time(row['date'])
                
                points.append(point)
            
            self.influx_write_api.write(bucket=bucket, record=points)
            logger.debug(f"Stored {len(points)} historical data points in InfluxDB")
            
        except Exception as e:
            logger.error(f"Failed to store historical data in InfluxDB: {str(e)}")
    
    async def _store_real_time_data_influx(self, data_point: MarketDataPoint):
        """Store real-time data point in InfluxDB"""
        try:
            bucket = os.getenv("INFLUXDB_BUCKET", "market-data")
            
            point = Point("real_time_data") \
                .tag("symbol", data_point.symbol) \
                .tag("source", data_point.source.value) \
                .field("open", data_point.open_price) \
                .field("high", data_point.high_price) \
                .field("low", data_point.low_price) \
                .field("close", data_point.close_price) \
                .field("volume", data_point.volume) \
                .time(data_point.timestamp)
            
            self.influx_write_api.write(bucket=bucket, record=point)
            logger.debug(f"Stored real-time data point for {data_point.symbol} in InfluxDB")
            
        except Exception as e:
            logger.error(f"Failed to store real-time data in InfluxDB: {str(e)}")
    
    async def start_background_ingestion(self, symbols: List[str], interval_seconds: int = 60):
        """Start background data ingestion for a list of symbols"""
        logger.info(f"Starting background ingestion for {len(symbols)} symbols")
        
        asyncio.create_task(self._background_ingestion_worker(symbols, interval_seconds))
    
    async def _background_ingestion_worker(self, symbols: List[str], interval_seconds: int):
        """Background worker for continuous data ingestion"""
        while self.is_running:
            try:
                for symbol in symbols:
                    try:
                        # Get real-time data
                        data_point = await self.get_real_time_data(symbol)
                        if data_point:
                            logger.debug(f"Ingested real-time data for {symbol}")
                    except Exception as e:
                        logger.error(f"Background ingestion error for {symbol}: {str(e)}")
                
                # Wait for next interval
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Background ingestion worker error: {str(e)}")
                await asyncio.sleep(interval_seconds)

# Singleton instance
data_ingestion_service = DataIngestionService()