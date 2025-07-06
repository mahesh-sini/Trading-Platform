import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from enum import Enum
# Using pure Python implementations for maximum compatibility

logger = logging.getLogger(__name__)

class FeatureType(Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    MACRO = "macro"
    ALTERNATIVE = "alternative"

@dataclass
class FeatureDefinition:
    name: str
    feature_type: FeatureType
    description: str
    dependencies: List[str]
    calculation_function: str

class FeatureService:
    def __init__(self):
        self.feature_cache = {}
        self.feature_definitions = {}
        self.initialize_features()
    
    async def initialize(self):
        """Initialize feature service"""
        logger.info("Initializing Feature Engineering Service")
        
    def initialize_features(self):
        """Initialize feature definitions"""
        self.feature_definitions = {
            # Price-based features
            'price_change_1d': FeatureDefinition(
                name='price_change_1d',
                feature_type=FeatureType.TECHNICAL,
                description='1-day price change percentage',
                dependencies=['close'],
                calculation_function='calculate_price_change'
            ),
            'price_change_5d': FeatureDefinition(
                name='price_change_5d',
                feature_type=FeatureType.TECHNICAL,
                description='5-day price change percentage',
                dependencies=['close'],
                calculation_function='calculate_price_change'
            ),
            
            # Moving averages
            'sma_5': FeatureDefinition(
                name='sma_5',
                feature_type=FeatureType.TECHNICAL,
                description='5-period Simple Moving Average',
                dependencies=['close'],
                calculation_function='calculate_sma'
            ),
            'sma_20': FeatureDefinition(
                name='sma_20',
                feature_type=FeatureType.TECHNICAL,
                description='20-period Simple Moving Average',
                dependencies=['close'],
                calculation_function='calculate_sma'
            ),
            'ema_12': FeatureDefinition(
                name='ema_12',
                feature_type=FeatureType.TECHNICAL,
                description='12-period Exponential Moving Average',
                dependencies=['close'],
                calculation_function='calculate_ema'
            ),
            
            # Technical indicators
            'rsi': FeatureDefinition(
                name='rsi',
                feature_type=FeatureType.TECHNICAL,
                description='Relative Strength Index',
                dependencies=['close'],
                calculation_function='calculate_rsi'
            ),
            'macd': FeatureDefinition(
                name='macd',
                feature_type=FeatureType.TECHNICAL,
                description='MACD Line',
                dependencies=['close'],
                calculation_function='calculate_macd'
            ),
            'bollinger_position': FeatureDefinition(
                name='bollinger_position',
                feature_type=FeatureType.TECHNICAL,
                description='Position within Bollinger Bands',
                dependencies=['close'],
                calculation_function='calculate_bollinger_position'
            ),
            
            # Volume indicators
            'volume_ratio': FeatureDefinition(
                name='volume_ratio',
                feature_type=FeatureType.TECHNICAL,
                description='Volume ratio vs average',
                dependencies=['volume'],
                calculation_function='calculate_volume_ratio'
            ),
            'volume_price_trend': FeatureDefinition(
                name='volume_price_trend',
                feature_type=FeatureType.TECHNICAL,
                description='Volume Price Trend indicator',
                dependencies=['close', 'volume'],
                calculation_function='calculate_vpt'
            ),
            
            # Volatility indicators
            'atr': FeatureDefinition(
                name='atr',
                feature_type=FeatureType.TECHNICAL,
                description='Average True Range',
                dependencies=['high', 'low', 'close'],
                calculation_function='calculate_atr'
            ),
            'volatility': FeatureDefinition(
                name='volatility',
                feature_type=FeatureType.TECHNICAL,
                description='Historical volatility',
                dependencies=['close'],
                calculation_function='calculate_volatility'
            ),
            
            # Pattern recognition
            'doji_pattern': FeatureDefinition(
                name='doji_pattern',
                feature_type=FeatureType.TECHNICAL,
                description='Doji candlestick pattern',
                dependencies=['open', 'high', 'low', 'close'],
                calculation_function='calculate_doji'
            ),
            'hammer_pattern': FeatureDefinition(
                name='hammer_pattern',
                feature_type=FeatureType.TECHNICAL,
                description='Hammer candlestick pattern',
                dependencies=['open', 'high', 'low', 'close'],
                calculation_function='calculate_hammer'
            )
        }
    
    async def extract_features(
        self, 
        data: pd.DataFrame, 
        feature_list: List[str] = None,
        symbol: str = None
    ) -> pd.DataFrame:
        """Extract features from market data"""
        try:
            if feature_list is None:
                feature_list = list(self.feature_definitions.keys())
            
            result_df = data.copy()
            
            # Calculate each requested feature
            for feature_name in feature_list:
                if feature_name in self.feature_definitions:
                    feature_def = self.feature_definitions[feature_name]
                    
                    # Check if dependencies are available
                    missing_deps = [dep for dep in feature_def.dependencies if dep not in data.columns]
                    if missing_deps:
                        logger.warning(f"Missing dependencies for {feature_name}: {missing_deps}")
                        continue
                    
                    # Calculate feature
                    feature_values = await self._calculate_feature(feature_name, data)
                    result_df[feature_name] = feature_values
                else:
                    logger.warning(f"Unknown feature: {feature_name}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            raise
    
    async def _calculate_feature(self, feature_name: str, data: pd.DataFrame) -> pd.Series:
        """Calculate a specific feature"""
        try:
            if feature_name == 'price_change_1d':
                return data['close'].pct_change(periods=1)
            
            elif feature_name == 'price_change_5d':
                return data['close'].pct_change(periods=5)
            
            elif feature_name == 'sma_5':
                return data['close'].rolling(window=5).mean()
            
            elif feature_name == 'sma_20':
                return data['close'].rolling(window=20).mean()
            
            elif feature_name == 'ema_12':
                return data['close'].ewm(span=12).mean()
            
            elif feature_name == 'rsi':
                return self._calculate_rsi(data['close'])
            
            elif feature_name == 'macd':
                return self._calculate_macd(data['close'])
            
            elif feature_name == 'bollinger_position':
                return self._calculate_bollinger_position(data['close'])
            
            elif feature_name == 'volume_ratio':
                volume_sma = data['volume'].rolling(window=10).mean()
                return data['volume'] / volume_sma
            
            elif feature_name == 'volume_price_trend':
                return self._calculate_vpt(data['close'], data['volume'])
            
            elif feature_name == 'atr':
                return self._calculate_atr(data['high'], data['low'], data['close'])
            
            elif feature_name == 'volatility':
                returns = data['close'].pct_change()
                return returns.rolling(window=20).std() * np.sqrt(252)  # Annualized
            
            elif feature_name == 'doji_pattern':
                return self._calculate_doji_pattern(data)
            
            elif feature_name == 'hammer_pattern':
                return self._calculate_hammer_pattern(data)
            
            else:
                logger.warning(f"Feature calculation not implemented: {feature_name}")
                return pd.Series([0] * len(data), index=data.index)
                
        except Exception as e:
            logger.error(f"Failed to calculate feature {feature_name}: {str(e)}")
            return pd.Series([0] * len(data), index=data.index)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        return ema_fast - ema_slow
    
    def _calculate_bollinger_position(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> pd.Series:
        """Calculate position within Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return (prices - lower_band) / (upper_band - lower_band)
    
    def _calculate_vpt(self, prices: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate Volume Price Trend"""
        price_change = prices.pct_change()
        vpt = (volume * price_change).cumsum()
        return vpt
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def _calculate_doji_pattern(self, data: pd.DataFrame) -> pd.Series:
        """Detect Doji candlestick pattern"""
        body_size = abs(data['close'] - data['open'])
        total_range = data['high'] - data['low']
        
        # Doji when body is very small relative to total range
        doji_threshold = 0.1
        return (body_size / total_range < doji_threshold).astype(int)
    
    def _calculate_hammer_pattern(self, data: pd.DataFrame) -> pd.Series:
        """Detect Hammer candlestick pattern"""
        body_size = abs(data['close'] - data['open'])
        lower_shadow = data[['open', 'close']].min(axis=1) - data['low']
        upper_shadow = data['high'] - data[['open', 'close']].max(axis=1)
        
        # Hammer: small body, long lower shadow, small upper shadow
        hammer = (
            (lower_shadow > body_size * 2) &
            (upper_shadow < body_size * 0.5) &
            (body_size > 0)
        ).astype(int)
        
        return hammer
    
    async def get_sentiment_features(self, symbol: str) -> Dict[str, float]:
        """Get sentiment-based features"""
        # TODO: Implement sentiment analysis
        # This would integrate with news APIs, social media, etc.
        return {
            'news_sentiment': 0.0,
            'social_sentiment': 0.0,
            'analyst_sentiment': 0.0
        }
    
    async def get_fundamental_features(self, symbol: str) -> Dict[str, float]:
        """Get fundamental analysis features"""
        # TODO: Implement fundamental analysis
        # This would integrate with financial data APIs
        return {
            'pe_ratio': 0.0,
            'pb_ratio': 0.0,
            'debt_to_equity': 0.0,
            'roe': 0.0,
            'revenue_growth': 0.0
        }
    
    async def get_macro_features(self) -> Dict[str, float]:
        """Get macroeconomic features"""
        # TODO: Implement macro indicators
        # This would integrate with economic data APIs
        return {
            'interest_rate': 0.0,
            'inflation_rate': 0.0,
            'gdp_growth': 0.0,
            'unemployment_rate': 0.0,
            'vix': 0.0
        }
    
    def get_feature_importance(self, model_type: str, symbol: str) -> Dict[str, float]:
        """Get feature importance from trained models"""
        # TODO: Implement feature importance extraction
        # This would analyze which features are most predictive
        return {}
    
    async def update_feature_cache(self, symbol: str, features: Dict[str, Any]):
        """Update feature cache"""
        cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d')}"
        self.feature_cache[cache_key] = {
            'features': features,
            'timestamp': datetime.now()
        }
    
    def get_cached_features(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached features if available"""
        cache_key = f"{symbol}_{datetime.now().strftime('%Y%m%d')}"
        cached_data = self.feature_cache.get(cache_key)
        
        if cached_data:
            # Check if cache is still valid (e.g., less than 1 hour old)
            age = datetime.now() - cached_data['timestamp']
            if age < timedelta(hours=1):
                return cached_data['features']
        
        return None

# Singleton instance
feature_service = FeatureService()