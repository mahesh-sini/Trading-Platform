"""
Indian Broker API Integrations
Supports Upstox, Zerodha, ICICI Breeze, and Angel One APIs
"""

import os
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import base64
import hashlib
import hmac
from dataclasses import dataclass

from monitoring.metrics import trading_metrics
from monitoring.logging_config import market_data_logger

logger = logging.getLogger(__name__)

@dataclass
class BrokerCredentials:
    """Broker API credentials"""
    api_key: str
    secret: str
    access_token: Optional[str] = None
    client_id: Optional[str] = None

class IndianBrokerAPIService:
    """Unified service for Indian broker APIs"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.credentials = self._load_credentials()
        self.base_urls = {
            'upstox': 'https://api.upstox.com/v2',
            'zerodha': 'https://api.kite.trade',
            'icici': 'https://api.icicidirect.com/breezeapi/api/v1',
            'angel_one': 'https://apiconnect.angelbroking.com'
        }
        
    def _load_credentials(self) -> Dict[str, BrokerCredentials]:
        """Load broker credentials from environment variables"""
        credentials = {}
        
        # Upstox
        if os.getenv('UPSTOX_API_KEY') and os.getenv('UPSTOX_SECRET'):
            credentials['upstox'] = BrokerCredentials(
                api_key=os.getenv('UPSTOX_API_KEY'),
                secret=os.getenv('UPSTOX_SECRET'),
                access_token=os.getenv('UPSTOX_ACCESS_TOKEN')
            )
            
        # Zerodha
        if os.getenv('ZERODHA_API_KEY') and os.getenv('ZERODHA_SECRET'):
            credentials['zerodha'] = BrokerCredentials(
                api_key=os.getenv('ZERODHA_API_KEY'),
                secret=os.getenv('ZERODHA_SECRET'),
                access_token=os.getenv('ZERODHA_ACCESS_TOKEN')
            )
            
        # ICICI Breeze
        if os.getenv('ICICI_BREEZE_API_KEY') and os.getenv('ICICI_BREEZE_SECRET'):
            credentials['icici'] = BrokerCredentials(
                api_key=os.getenv('ICICI_BREEZE_API_KEY'),
                secret=os.getenv('ICICI_BREEZE_SECRET'),
                access_token=os.getenv('ICICI_BREEZE_SESSION_TOKEN')
            )
            
        # Angel One
        if os.getenv('ANGEL_ONE_API_KEY') and os.getenv('ANGEL_ONE_CLIENT_ID'):
            credentials['angel_one'] = BrokerCredentials(
                api_key=os.getenv('ANGEL_ONE_API_KEY'),
                secret=os.getenv('ANGEL_ONE_PASSWORD', ''),
                client_id=os.getenv('ANGEL_ONE_CLIENT_ID'),
                access_token=os.getenv('ANGEL_ONE_JWT_TOKEN')
            )
            
        return credentials
    
    async def ensure_session(self):
        """Ensure HTTP session is available"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={'User-Agent': 'AI-Trading-Platform/1.0'}
            )
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    # UPSTOX API Integration
    async def get_upstox_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live quote from Upstox API"""
        try:
            if 'upstox' not in self.credentials:
                return None
                
            await self.ensure_session()
            creds = self.credentials['upstox']
            
            # Convert symbol to Upstox format
            instrument_key = f"NSE_EQ|INE{symbol}"  # Simplified conversion
            
            url = f"{self.base_urls['upstox']}/market-quote/ltp"
            headers = {
                'Authorization': f'Bearer {creds.access_token}',
                'Accept': 'application/json'
            }
            params = {'instrument_key': instrument_key}
            
            async with self.session.get(url, headers=headers, params=params) as response:
                trading_metrics.record_provider_api_call({
                    'provider': 'upstox',
                    'endpoint': 'market-quote/ltp',
                    'status': 'success' if response.status == 200 else 'error'
                })
                
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_upstox_quote(data, symbol)
                else:
                    trading_metrics.record_provider_error({
                        'provider': 'upstox',
                        'error_type': f'http_{response.status}'
                    })
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Upstox quote for {symbol}: {e}")
            trading_metrics.record_provider_error({
                'provider': 'upstox',
                'error_type': 'api_exception'
            })
            return None
    
    # ZERODHA API Integration
    async def get_zerodha_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live quote from Zerodha Kite API"""
        try:
            if 'zerodha' not in self.credentials:
                return None
                
            await self.ensure_session()
            creds = self.credentials['zerodha']
            
            # Convert symbol to Zerodha format
            instrument = f"NSE:{symbol}"
            
            url = f"{self.base_urls['zerodha']}/quote/ltp"
            headers = {
                'X-Kite-Version': '3',
                'Authorization': f'token {creds.api_key}:{creds.access_token}'
            }
            params = {'i': instrument}
            
            async with self.session.get(url, headers=headers, params=params) as response:
                trading_metrics.record_provider_api_call({
                    'provider': 'zerodha',
                    'endpoint': 'quote/ltp',
                    'status': 'success' if response.status == 200 else 'error'
                })
                
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_zerodha_quote(data, symbol)
                else:
                    trading_metrics.record_provider_error({
                        'provider': 'zerodha',
                        'error_type': f'http_{response.status}'
                    })
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Zerodha quote for {symbol}: {e}")
            trading_metrics.record_provider_error({
                'provider': 'zerodha',
                'error_type': 'api_exception'
            })
            return None
    
    # ICICI BREEZE API Integration
    async def get_icici_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live quote from ICICI Breeze API"""
        try:
            if 'icici' not in self.credentials:
                return None
                
            await self.ensure_session()
            creds = self.credentials['icici']
            
            url = f"{self.base_urls['icici']}/getquotes"
            headers = {
                'X-SessionToken': creds.access_token,
                'Content-Type': 'application/json'
            }
            payload = {
                'stock_code': symbol,
                'exchange_code': 'NSE'
            }
            
            async with self.session.post(url, headers=headers, json=payload) as response:
                trading_metrics.record_provider_api_call({
                    'provider': 'icici',
                    'endpoint': 'getquotes',
                    'status': 'success' if response.status == 200 else 'error'
                })
                
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_icici_quote(data, symbol)
                else:
                    trading_metrics.record_provider_error({
                        'provider': 'icici',
                        'error_type': f'http_{response.status}'
                    })
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching ICICI quote for {symbol}: {e}")
            trading_metrics.record_provider_error({
                'provider': 'icici',
                'error_type': 'api_exception'
            })
            return None
    
    # ANGEL ONE API Integration
    async def get_angel_one_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live quote from Angel One SmartAPI"""
        try:
            if 'angel_one' not in self.credentials:
                return None
                
            await self.ensure_session()
            creds = self.credentials['angel_one']
            
            url = f"{self.base_urls['angel_one']}/rest/secure/angelbroking/order/v1/getLTP"
            headers = {
                'Authorization': f'Bearer {creds.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-UserType': 'USER',
                'X-SourceID': 'WEB',
                'X-ClientLocalIP': '127.0.0.1',
                'X-ClientPublicIP': '127.0.0.1',
                'X-MACAddress': '00:00:00:00:00:00',
                'X-PrivateKey': creds.api_key
            }
            payload = {
                'exchange': 'NSE',
                'tradingsymbol': symbol,
                'symboltoken': ''  # Would need to be mapped from symbol master
            }
            
            async with self.session.post(url, headers=headers, json=payload) as response:
                trading_metrics.record_provider_api_call({
                    'provider': 'angel_one',
                    'endpoint': 'getLTP',
                    'status': 'success' if response.status == 200 else 'error'
                })
                
                if response.status == 200:
                    data = await response.json()
                    return self._normalize_angel_one_quote(data, symbol)
                else:
                    trading_metrics.record_provider_error({
                        'provider': 'angel_one',
                        'error_type': f'http_{response.status}'
                    })
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching Angel One quote for {symbol}: {e}")
            trading_metrics.record_provider_error({
                'provider': 'angel_one',
                'error_type': 'api_exception'
            })
            return None
    
    # Quote normalization methods
    def _normalize_upstox_quote(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Normalize Upstox quote data"""
        try:
            if data.get('status') == 'success' and data.get('data'):
                quote_data = list(data['data'].values())[0]
                return {
                    'symbol': symbol,
                    'price': float(quote_data.get('last_price', 0)),
                    'change': 0,  # Calculate from previous close
                    'change_percent': 0,
                    'volume': quote_data.get('volume', 0),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'provider': 'upstox'
                }
        except Exception as e:
            logger.error(f"Error normalizing Upstox quote: {e}")
        return None
    
    def _normalize_zerodha_quote(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Normalize Zerodha quote data"""
        try:
            if data.get('status') == 'success' and data.get('data'):
                instrument_key = f"NSE:{symbol}"
                quote_data = data['data'].get(instrument_key, {})
                return {
                    'symbol': symbol,
                    'price': float(quote_data.get('last_price', 0)),
                    'change': 0,
                    'change_percent': 0,
                    'volume': quote_data.get('volume', 0),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'provider': 'zerodha'
                }
        except Exception as e:
            logger.error(f"Error normalizing Zerodha quote: {e}")
        return None
    
    def _normalize_icici_quote(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Normalize ICICI quote data"""
        try:
            if data.get('Success') and data.get('Success').get('stock_code') == symbol:
                quote_data = data['Success']
                return {
                    'symbol': symbol,
                    'price': float(quote_data.get('ltp', 0)),
                    'change': float(quote_data.get('change', 0)),
                    'change_percent': float(quote_data.get('percentage_change', 0)),
                    'volume': quote_data.get('volume', 0),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'provider': 'icici'
                }
        except Exception as e:
            logger.error(f"Error normalizing ICICI quote: {e}")
        return None
    
    def _normalize_angel_one_quote(self, data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Normalize Angel One quote data"""
        try:
            if data.get('status') and data.get('data'):
                quote_data = data['data']
                return {
                    'symbol': symbol,
                    'price': float(quote_data.get('ltp', 0)),
                    'change': 0,
                    'change_percent': 0,
                    'volume': quote_data.get('volume', 0),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'provider': 'angel_one'
                }
        except Exception as e:
            logger.error(f"Error normalizing Angel One quote: {e}")
        return None
    
    async def get_best_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get best available quote from all enabled Indian brokers"""
        quote_tasks = []
        
        # Create tasks for all available providers
        if 'upstox' in self.credentials:
            quote_tasks.append(('upstox', self.get_upstox_quote(symbol)))
        if 'zerodha' in self.credentials:
            quote_tasks.append(('zerodha', self.get_zerodha_quote(symbol)))
        if 'icici' in self.credentials:
            quote_tasks.append(('icici', self.get_icici_quote(symbol)))
        if 'angel_one' in self.credentials:
            quote_tasks.append(('angel_one', self.get_angel_one_quote(symbol)))
        
        if not quote_tasks:
            return None
        
        # Execute all tasks concurrently
        import asyncio
        results = await asyncio.gather(*[task for _, task in quote_tasks], return_exceptions=True)
        
        # Return first successful quote
        for i, result in enumerate(results):
            if result and not isinstance(result, Exception):
                provider_name = quote_tasks[i][0]
                market_data_logger.info(f"Successfully fetched quote for {symbol} from {provider_name}")
                return result
        
        logger.warning(f"No quotes available for {symbol} from any Indian broker")
        return None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available broker providers"""
        return list(self.credentials.keys())
    
    def is_provider_enabled(self, provider: str) -> bool:
        """Check if a specific provider is enabled"""
        return provider in self.credentials