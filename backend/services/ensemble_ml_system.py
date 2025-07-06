"""
Ensemble ML System for Trading Predictions
Implements 4-model ensemble with different time horizons and meta-learner
"""

import numpy as np
import pandas as pd
import sqlite3
import logging
import joblib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import json

# ML libraries
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

# Technical analysis (using pandas implementation)
# import talib

logger = logging.getLogger(__name__)

class ModelType(Enum):
    SHORT_TERM = "short_term"      # 30 days, daily retraining
    MEDIUM_TERM = "medium_term"    # 90 days, weekly retraining  
    LONG_TERM = "long_term"        # 252 days, monthly retraining
    FUNDAMENTAL = "fundamental"    # 1+ years, quarterly retraining

class PredictionHorizon(Enum):
    NEXT_DAY = 1
    NEXT_WEEK = 5
    NEXT_MONTH = 22

@dataclass
class ModelPrediction:
    model_type: ModelType
    symbol: str
    exchange: str
    prediction: float
    confidence: float
    features_used: List[str]
    training_period: int
    prediction_horizon: PredictionHorizon
    created_at: datetime

@dataclass
class EnsemblePrediction:
    symbol: str
    exchange: str
    final_prediction: float
    confidence: float
    model_predictions: List[ModelPrediction]
    meta_learner_weights: Dict[str, float]
    prediction_horizon: PredictionHorizon
    created_at: datetime

class FeatureEngineer:
    """Advanced feature engineering for trading data"""
    
    def __init__(self):
        self.technical_periods = {
            'sma_short': [5, 10, 20],
            'sma_long': [50, 100, 200],
            'ema': [12, 26, 50],
            'rsi': [14, 21],
            'macd': [(12, 26, 9)],
            'bb': [(20, 2)],
            'stoch': [(14, 3, 3)]
        }
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer comprehensive trading features"""
        features_df = df.copy()
        
        # Price-based features
        features_df['returns'] = features_df['close'].pct_change()
        features_df['log_returns'] = np.log(features_df['close'] / features_df['close'].shift(1))
        features_df['price_range'] = (features_df['high'] - features_df['low']) / features_df['close']
        features_df['gap'] = (features_df['open'] - features_df['close'].shift(1)) / features_df['close'].shift(1)
        
        # Volume features
        features_df['volume_sma'] = features_df['volume'].rolling(20).mean()
        features_df['volume_ratio'] = features_df['volume'] / features_df['volume_sma']
        features_df['price_volume'] = features_df['close'] * features_df['volume']
        
        # Technical indicators
        self._add_moving_averages(features_df)
        self._add_momentum_indicators(features_df)
        self._add_volatility_indicators(features_df)
        self._add_volume_indicators(features_df)
        
        # Lag features
        for lag in [1, 2, 3, 5, 10]:
            features_df[f'returns_lag_{lag}'] = features_df['returns'].shift(lag)
            features_df[f'volume_ratio_lag_{lag}'] = features_df['volume_ratio'].shift(lag)
        
        # Rolling statistics
        for window in [5, 10, 20]:
            features_df[f'returns_mean_{window}'] = features_df['returns'].rolling(window).mean()
            features_df[f'returns_std_{window}'] = features_df['returns'].rolling(window).std()
            features_df[f'volume_mean_{window}'] = features_df['volume'].rolling(window).mean()
        
        return features_df
    
    def _add_moving_averages(self, df: pd.DataFrame):
        """Add moving average indicators"""
        # Simple Moving Averages
        for period in self.technical_periods['sma_short'] + self.technical_periods['sma_long']:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
        
        # Exponential Moving Averages
        for period in self.technical_periods['ema']:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            df[f'ema_{period}_ratio'] = df['close'] / df[f'ema_{period}']
    
    def _add_momentum_indicators(self, df: pd.DataFrame):
        """Add momentum indicators"""
        # RSI (simplified calculation)
        for period in self.technical_periods['rsi']:
            df[f'rsi_{period}'] = self._calculate_rsi(df['close'], period)
        
        # MACD
        for fast, slow, signal in self.technical_periods['macd']:
            ema_fast = df['close'].ewm(span=fast).mean()
            ema_slow = df['close'].ewm(span=slow).mean()
            df['macd'] = ema_fast - ema_slow
            df['macd_signal'] = df['macd'].ewm(span=signal).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Rate of Change
        df['roc_10'] = df['close'].pct_change(10) * 100
        df['roc_20'] = df['close'].pct_change(20) * 100
    
    def _add_volatility_indicators(self, df: pd.DataFrame):
        """Add volatility indicators"""
        # Bollinger Bands
        for period, std_dev in self.technical_periods['bb']:
            middle = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            df[f'bb_upper_{period}'] = upper
            df[f'bb_middle_{period}'] = middle
            df[f'bb_lower_{period}'] = lower
            df[f'bb_width_{period}'] = (upper - lower) / middle
            df[f'bb_position_{period}'] = (df['close'] - lower) / (upper - lower)
        
        # Average True Range (simplified)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        df['atr_14'] = true_range.rolling(window=14).mean()
        df['atr_ratio'] = df['atr_14'] / df['close']
    
    def _add_volume_indicators(self, df: pd.DataFrame):
        """Add volume-based indicators"""
        # On Balance Volume (simplified)
        df['price_change'] = df['close'].diff()
        df['obv'] = (df['volume'] * np.sign(df['price_change'])).cumsum()
        df['obv_sma'] = df['obv'].rolling(20).mean()
        df['obv_ratio'] = df['obv'] / df['obv_sma']
        
        # Volume Rate of Change
        df['volume_roc'] = df['volume'].pct_change(10)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI using pandas"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

class BaseMLModel:
    """Base class for individual ML models in the ensemble"""
    
    def __init__(self, model_type: ModelType, symbol: str, exchange: str):
        self.model_type = model_type
        self.symbol = symbol
        self.exchange = exchange
        self.model = None
        self.scaler = None
        self.feature_engineer = FeatureEngineer()
        self.feature_columns = []
        self.training_config = self._get_training_config()
        
    def _get_training_config(self) -> Dict[str, Any]:
        """Get training configuration based on model type"""
        configs = {
            ModelType.SHORT_TERM: {
                "lookback_days": 30,
                "prediction_horizon": PredictionHorizon.NEXT_DAY,
                "features_focus": ["price", "volume", "momentum"],
                "model_class": "lgb",
                "retrain_frequency": "daily"
            },
            ModelType.MEDIUM_TERM: {
                "lookback_days": 90,
                "prediction_horizon": PredictionHorizon.NEXT_WEEK,
                "features_focus": ["price", "technical", "momentum"],
                "model_class": "xgb",
                "retrain_frequency": "weekly"
            },
            ModelType.LONG_TERM: {
                "lookback_days": 252,
                "prediction_horizon": PredictionHorizon.NEXT_MONTH,
                "features_focus": ["technical", "fundamental", "macro"],
                "model_class": "rf",
                "retrain_frequency": "monthly"
            },
            ModelType.FUNDAMENTAL: {
                "lookback_days": 504,
                "prediction_horizon": PredictionHorizon.NEXT_MONTH,
                "features_focus": ["fundamental", "macro", "sector"],
                "model_class": "gbm",
                "retrain_frequency": "quarterly"
            }
        }
        return configs[self.model_type]
    
    def _initialize_model(self):
        """Initialize the appropriate ML model"""
        model_class = self.training_config["model_class"]
        
        if model_class == "lgb" and HAS_LGB:
            self.model = lgb.LGBMRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42,
                objective='regression'
            )
        elif model_class == "xgb" and HAS_XGB:
            self.model = xgb.XGBRegressor(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=6,
                random_state=42,
                objective='reg:squarederror'
            )
        elif model_class == "rf":
            self.model = RandomForestRegressor(
                n_estimators=200,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
        else:  # Fallback to GBM
            self.model = GradientBoostingRegressor(
                n_estimators=150,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
        
        self.scaler = RobustScaler()
    
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features based on model type focus"""
        # Engineer all features
        features_df = self.feature_engineer.engineer_features(df)
        
        # Select relevant features based on model focus
        focus_areas = self.training_config["features_focus"]
        selected_features = []
        
        if "price" in focus_areas:
            selected_features.extend([
                'returns', 'log_returns', 'price_range', 'gap',
                'returns_lag_1', 'returns_lag_2', 'returns_lag_3'
            ])
        
        if "volume" in focus_areas:
            selected_features.extend([
                'volume_ratio', 'volume_roc', 'obv_ratio',
                'volume_ratio_lag_1', 'volume_ratio_lag_2'
            ])
        
        if "momentum" in focus_areas:
            selected_features.extend([
                'rsi_14', 'rsi_21', 'macd', 'macd_histogram',
                'roc_10', 'roc_20'
            ])
        
        if "technical" in focus_areas:
            selected_features.extend([
                'sma_5_ratio', 'sma_20_ratio', 'sma_50_ratio',
                'ema_12_ratio', 'ema_26_ratio', 'bb_position_20',
                'bb_width_20', 'atr_ratio'
            ])
        
        if "fundamental" in focus_areas:
            # Placeholder for fundamental features (would be added from financial data)
            selected_features.extend([
                'returns_mean_20', 'returns_std_20',
                'volume_mean_20'
            ])
        
        # Filter features that exist in the dataframe
        available_features = [f for f in selected_features if f in features_df.columns]
        self.feature_columns = available_features
        
        return features_df[available_features].dropna()
    
    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train the model"""
        try:
            # Initialize model
            self._initialize_model()
            
            # Prepare features
            features_df = self.prepare_features(df)
            
            if len(features_df) < 50:  # Minimum data requirement
                raise ValueError(f"Insufficient data for training: {len(features_df)} rows")
            
            # Prepare target variable (next period return)
            horizon_days = self.training_config["prediction_horizon"].value
            target = df['close'].pct_change(horizon_days).shift(-horizon_days)
            
            # Align features and target
            aligned_target = target.loc[features_df.index]
            
            # Remove NaN values
            valid_idx = ~(features_df.isnull().any(axis=1) | aligned_target.isnull())
            X = features_df[valid_idx]
            y = aligned_target[valid_idx]
            
            if len(X) < 30:
                raise ValueError(f"Insufficient valid data after cleaning: {len(X)} rows")
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train model
            self.model.fit(X_scaled, y)
            
            # Evaluate model
            train_score = self.model.score(X_scaled, y)
            predictions = self.model.predict(X_scaled)
            mse = mean_squared_error(y, predictions)
            mae = mean_absolute_error(y, predictions)
            
            training_stats = {
                "train_r2": train_score,
                "train_mse": mse,
                "train_mae": mae,
                "features_count": len(self.feature_columns),
                "training_samples": len(X),
                "feature_importance": self._get_feature_importance()
            }
            
            logger.info(f"Trained {self.model_type.value} model for {self.symbol}: R²={train_score:.3f}")
            return training_stats
            
        except Exception as e:
            logger.error(f"Error training {self.model_type.value} model for {self.symbol}: {e}")
            raise
    
    def predict(self, df: pd.DataFrame) -> ModelPrediction:
        """Make prediction using trained model"""
        try:
            if self.model is None or self.scaler is None:
                raise ValueError("Model not trained")
            
            # Prepare features for the last available data point
            features_df = self.prepare_features(df)
            
            if len(features_df) == 0:
                raise ValueError("No valid features for prediction")
            
            # Get latest features
            latest_features = features_df.iloc[-1:].values
            latest_features_scaled = self.scaler.transform(latest_features)
            
            # Make prediction
            prediction = self.model.predict(latest_features_scaled)[0]
            
            # Calculate confidence (simplified - could be improved with uncertainty quantification)
            if hasattr(self.model, 'predict_proba'):
                confidence = 0.8  # Placeholder
            else:
                # Use feature stability as confidence proxy
                recent_features = features_df.iloc[-5:] if len(features_df) >= 5 else features_df
                feature_std = recent_features.std().mean()
                confidence = max(0.3, min(0.95, 1.0 - feature_std))
            
            return ModelPrediction(
                model_type=self.model_type,
                symbol=self.symbol,
                exchange=self.exchange,
                prediction=prediction,
                confidence=confidence,
                features_used=self.feature_columns,
                training_period=self.training_config["lookback_days"],
                prediction_horizon=self.training_config["prediction_horizon"],
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error making prediction with {self.model_type.value} model: {e}")
            raise
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance if available"""
        try:
            if hasattr(self.model, 'feature_importances_'):
                importance_dict = dict(zip(self.feature_columns, self.model.feature_importances_))
                return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            else:
                return {}
        except:
            return {}
    
    def save_model(self, path: Path):
        """Save trained model"""
        model_data = {
            "model": self.model,
            "scaler": self.scaler,
            "feature_columns": self.feature_columns,
            "training_config": self.training_config,
            "model_type": self.model_type.value,
            "symbol": self.symbol,
            "exchange": self.exchange
        }
        joblib.dump(model_data, path)
    
    def load_model(self, path: Path):
        """Load trained model"""
        model_data = joblib.load(path)
        self.model = model_data["model"]
        self.scaler = model_data["scaler"]
        self.feature_columns = model_data["feature_columns"]
        self.training_config = model_data["training_config"]

class MetaLearner:
    """Meta-learner that combines predictions from individual models"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.is_trained = False
        
    def train(self, historical_predictions: List[Dict[str, Any]], actual_returns: List[float]):
        """Train meta-learner on historical model predictions"""
        try:
            if len(historical_predictions) < 50:
                logger.warning("Insufficient data for meta-learner training, using simple average")
                return False
            
            # Prepare features (predictions from individual models)
            X = []
            for pred_set in historical_predictions:
                features = [
                    pred_set.get('short_term', 0),
                    pred_set.get('medium_term', 0),
                    pred_set.get('long_term', 0),
                    pred_set.get('fundamental', 0),
                    pred_set.get('short_term_confidence', 0.5),
                    pred_set.get('medium_term_confidence', 0.5),
                    pred_set.get('long_term_confidence', 0.5),
                    pred_set.get('fundamental_confidence', 0.5)
                ]
                X.append(features)
            
            X = np.array(X)
            y = np.array(actual_returns)
            
            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Train meta-learner (Ridge regression for stability)
            self.model = Ridge(alpha=1.0)
            self.model.fit(X_scaled, y)
            
            self.is_trained = True
            
            # Evaluate
            score = self.model.score(X_scaled, y)
            logger.info(f"Meta-learner trained with R² = {score:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training meta-learner: {e}")
            return False
    
    def combine_predictions(self, model_predictions: List[ModelPrediction]) -> Tuple[float, Dict[str, float]]:
        """Combine individual model predictions"""
        if not self.is_trained or self.model is None:
            # Simple weighted average based on confidence
            weights = []
            predictions = []
            
            for pred in model_predictions:
                weights.append(pred.confidence)
                predictions.append(pred.prediction)
            
            if not weights:
                return 0.0, {}
            
            weights = np.array(weights)
            weights = weights / weights.sum()  # Normalize
            
            combined_prediction = np.sum(np.array(predictions) * weights)
            
            # Create weight dictionary
            weight_dict = {}
            for i, pred in enumerate(model_predictions):
                weight_dict[pred.model_type.value] = float(weights[i])
            
            return combined_prediction, weight_dict
        
        else:
            # Use trained meta-learner
            features = [0] * 8  # Initialize with zeros
            
            for pred in model_predictions:
                if pred.model_type == ModelType.SHORT_TERM:
                    features[0] = pred.prediction
                    features[4] = pred.confidence
                elif pred.model_type == ModelType.MEDIUM_TERM:
                    features[1] = pred.prediction
                    features[5] = pred.confidence
                elif pred.model_type == ModelType.LONG_TERM:
                    features[2] = pred.prediction
                    features[6] = pred.confidence
                elif pred.model_type == ModelType.FUNDAMENTAL:
                    features[3] = pred.prediction
                    features[7] = pred.confidence
            
            X = np.array([features])
            X_scaled = self.scaler.transform(X)
            
            combined_prediction = self.model.predict(X_scaled)[0]
            
            # Get feature importance as weights (simplified)
            if hasattr(self.model, 'coef_'):
                coefs = np.abs(self.model.coef_[:4])  # First 4 features are predictions
                weights = coefs / coefs.sum() if coefs.sum() > 0 else np.ones(4) / 4
                
                weight_dict = {
                    'short_term': float(weights[0]),
                    'medium_term': float(weights[1]),
                    'long_term': float(weights[2]),
                    'fundamental': float(weights[3])
                }
            else:
                weight_dict = {'ensemble': 1.0}
            
            return combined_prediction, weight_dict

class EnsembleMLSystem:
    """Main ensemble ML system coordinating all models"""
    
    def __init__(self, db_path="trading_platform.db", models_dir="models/ensemble"):
        self.db_path = db_path
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.meta_learner = MetaLearner()
        self.trained_symbols = set()
        
    def get_training_data(self, symbol: str, exchange: str, lookback_days: int = 504) -> pd.DataFrame:
        """Get training data from bhav copies"""
        conn = sqlite3.connect(self.db_path)
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            query = """
                SELECT date, open, high, low, close, total_traded_qty as volume
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
                logger.warning(f"No training data found for {symbol} ({exchange})")
                return pd.DataFrame()
            
            # Convert and clean data
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            logger.info(f"Retrieved {len(df)} training data points for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting training data for {symbol}: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    async def train_ensemble_for_symbol(self, symbol: str, exchange: str) -> Dict[str, Any]:
        """Train all models in the ensemble for a specific symbol"""
        try:
            logger.info(f"🤖 Training ensemble for {symbol} ({exchange})")
            
            # Get training data
            df = self.get_training_data(symbol, exchange)
            
            if len(df) < 100:
                raise ValueError(f"Insufficient training data: {len(df)} rows")
            
            # Initialize models
            models = {
                ModelType.SHORT_TERM: BaseMLModel(ModelType.SHORT_TERM, symbol, exchange),
                ModelType.MEDIUM_TERM: BaseMLModel(ModelType.MEDIUM_TERM, symbol, exchange),
                ModelType.LONG_TERM: BaseMLModel(ModelType.LONG_TERM, symbol, exchange),
                ModelType.FUNDAMENTAL: BaseMLModel(ModelType.FUNDAMENTAL, symbol, exchange)
            }
            
            training_results = {}
            
            # Train each model
            for model_type, model in models.items():
                try:
                    # Get appropriate data window for this model
                    lookback = model.training_config["lookback_days"]
                    model_data = df.iloc[-lookback:] if len(df) > lookback else df
                    
                    # Train model
                    stats = model.train(model_data)
                    training_results[model_type.value] = stats
                    
                    # Save model
                    model_path = self.models_dir / f"{symbol}_{exchange}_{model_type.value}.pkl"
                    model.save_model(model_path)
                    
                    logger.info(f"  ✅ {model_type.value}: R²={stats['train_r2']:.3f}")
                    
                except Exception as e:
                    logger.error(f"  ❌ Failed to train {model_type.value}: {e}")
                    training_results[model_type.value] = {"error": str(e)}
            
            # Mark symbol as trained
            self.trained_symbols.add(f"{symbol}_{exchange}")
            
            # Overall results
            successful_models = sum(1 for result in training_results.values() if "error" not in result)
            
            ensemble_stats = {
                "symbol": symbol,
                "exchange": exchange,
                "successful_models": successful_models,
                "total_models": len(models),
                "training_data_points": len(df),
                "model_results": training_results,
                "trained_at": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Ensemble training completed: {successful_models}/{len(models)} models successful")
            return ensemble_stats
            
        except Exception as e:
            logger.error(f"Error training ensemble for {symbol}: {e}")
            return {"error": str(e)}
    
    async def get_ensemble_prediction(self, symbol: str, exchange: str) -> Optional[EnsemblePrediction]:
        """Get ensemble prediction for a symbol"""
        try:
            # Get latest data
            df = self.get_training_data(symbol, exchange, lookback_days=60)
            
            if len(df) < 30:
                logger.warning(f"Insufficient data for prediction: {len(df)} rows")
                return None
            
            # Load and predict with each model
            model_predictions = []
            
            for model_type in ModelType:
                try:
                    model_path = self.models_dir / f"{symbol}_{exchange}_{model_type.value}.pkl"
                    
                    if not model_path.exists():
                        logger.warning(f"Model not found: {model_path}")
                        continue
                    
                    # Load model
                    model = BaseMLModel(model_type, symbol, exchange)
                    model.load_model(model_path)
                    
                    # Make prediction
                    prediction = model.predict(df)
                    model_predictions.append(prediction)
                    
                except Exception as e:
                    logger.error(f"Error with {model_type.value} prediction: {e}")
                    continue
            
            if not model_predictions:
                logger.error("No models available for prediction")
                return None
            
            # Combine predictions using meta-learner
            combined_prediction, weights = self.meta_learner.combine_predictions(model_predictions)
            
            # Calculate overall confidence
            confidences = [pred.confidence for pred in model_predictions]
            overall_confidence = np.mean(confidences) if confidences else 0.5
            
            return EnsemblePrediction(
                symbol=symbol,
                exchange=exchange,
                final_prediction=combined_prediction,
                confidence=overall_confidence,
                model_predictions=model_predictions,
                meta_learner_weights=weights,
                prediction_horizon=PredictionHorizon.NEXT_DAY,  # Can be made configurable
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting ensemble prediction for {symbol}: {e}")
            return None
    
    async def train_all_symbols(self) -> Dict[str, Any]:
        """Train ensemble models for all symbols in the database"""
        try:
            # Get all symbols
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT symbol, exchange 
                FROM stock_symbols 
                WHERE status = 'ACTIVE' AND is_fo_enabled = 1
                ORDER BY market_cap DESC NULLS LAST
                LIMIT 50
            """)
            
            symbols = cursor.fetchall()
            conn.close()
            
            logger.info(f"🚀 Training ensemble models for {len(symbols)} symbols")
            
            results = {
                "total_symbols": len(symbols),
                "successful_trainings": 0,
                "failed_trainings": 0,
                "training_results": [],
                "start_time": datetime.now().isoformat()
            }
            
            # Train each symbol
            for i, (symbol, exchange) in enumerate(symbols, 1):
                try:
                    logger.info(f"[{i}/{len(symbols)}] Training {symbol} ({exchange})")
                    
                    training_result = await self.train_ensemble_for_symbol(symbol, exchange)
                    
                    if "error" in training_result:
                        results["failed_trainings"] += 1
                    else:
                        results["successful_trainings"] += 1
                    
                    results["training_results"].append(training_result)
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error training {symbol}: {e}")
                    results["failed_trainings"] += 1
                    results["training_results"].append({
                        "symbol": symbol,
                        "exchange": exchange,
                        "error": str(e)
                    })
            
            results["end_time"] = datetime.now().isoformat()
            results["success_rate"] = (results["successful_trainings"] / results["total_symbols"]) * 100
            
            logger.info(f"✅ Ensemble training completed!")
            logger.info(f"📊 Success rate: {results['success_rate']:.1f}%")
            logger.info(f"✅ Successful: {results['successful_trainings']}")
            logger.info(f"❌ Failed: {results['failed_trainings']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk training: {e}")
            return {"error": str(e)}

# Global instance
ensemble_ml_system = EnsembleMLSystem()