import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import joblib
import os
from pathlib import Path

# ML libraries
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, accuracy_score, classification_report
import xgboost as xgb
from tensorflow.keras.models import Sequential, load_model as keras_load_model
from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

logger = logging.getLogger(__name__)

class ModelType(Enum):
    LSTM = "lstm"
    GRU = "gru"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    ENSEMBLE = "ensemble"

class PredictionTimeframe(Enum):
    INTRADAY = "intraday"
    SWING = "swing"
    LONG_TERM = "long_term"

@dataclass
class PredictionRequest:
    symbol: str
    timeframe: PredictionTimeframe
    horizon: str  # "1h", "4h", "1d", "7d", etc.
    features: Optional[Dict[str, Any]] = None

@dataclass
class PredictionResult:
    symbol: str
    predicted_price: float
    current_price: float
    predicted_direction: str  # "up", "down", "sideways"
    confidence_score: float
    model_version: str
    features_used: List[str]
    prediction_horizon: str
    created_at: datetime

@dataclass
class ModelPerformance:
    model_name: str
    model_version: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    mse: float
    mae: float
    directional_accuracy: float

class MLModel:
    def __init__(self, model_type: ModelType, symbol: str, timeframe: PredictionTimeframe):
        self.model_type = model_type
        self.symbol = symbol
        self.timeframe = timeframe
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.version = "1.0"
        self.performance_metrics = {}
        
    def prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for training/prediction"""
        # Technical indicators
        data['sma_5'] = data['close'].rolling(window=5).mean()
        data['sma_20'] = data['close'].rolling(window=20).mean()
        data['ema_12'] = data['close'].ewm(span=12).mean()
        data['ema_26'] = data['close'].ewm(span=26).mean()
        
        # MACD
        data['macd'] = data['ema_12'] - data['ema_26']
        data['macd_signal'] = data['macd'].ewm(span=9).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        bb_period = 20
        data['bb_middle'] = data['close'].rolling(window=bb_period).mean()
        bb_std = data['close'].rolling(window=bb_period).std()
        data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
        data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
        data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
        
        # Volume indicators
        data['volume_sma'] = data['volume'].rolling(window=10).mean()
        data['volume_ratio'] = data['volume'] / data['volume_sma']
        
        # Price changes
        data['price_change'] = data['close'].pct_change()
        data['price_change_1d'] = data['close'].pct_change(periods=1)
        data['price_change_5d'] = data['close'].pct_change(periods=5)
        
        # Volatility
        data['volatility'] = data['price_change'].rolling(window=20).std()
        
        # Feature columns
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'sma_5', 'sma_20', 'ema_12', 'ema_26',
            'macd', 'macd_signal', 'macd_histogram',
            'rsi', 'bb_position', 'volume_ratio',
            'price_change_1d', 'price_change_5d', 'volatility'
        ]
        
        # Create target variable (next period's price change)
        data['target'] = data['close'].shift(-1) / data['close'] - 1
        data['target_direction'] = (data['target'] > 0).astype(int)
        
        # Drop NaN values
        data = data.dropna()
        
        X = data[feature_cols].values
        y_price = data['target'].values
        y_direction = data['target_direction'].values
        
        return X, y_price, y_direction
    
    def train(self, data: pd.DataFrame) -> Dict[str, float]:
        """Train the ML model"""
        try:
            X, y_price, y_direction = self.prepare_features(data)
            
            if len(X) < 100:
                raise ValueError("Insufficient data for training")
            
            # Split data for time series
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_price_train, y_price_test = y_price[:split_idx], y_price[split_idx:]
            y_direction_train, y_direction_test = y_direction[:split_idx], y_direction[split_idx:]
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            if self.model_type == ModelType.RANDOM_FOREST:
                self.model = {
                    'price': RandomForestRegressor(n_estimators=100, random_state=42),
                    'direction': RandomForestClassifier(n_estimators=100, random_state=42)
                }
                self.model['price'].fit(X_train_scaled, y_price_train)
                self.model['direction'].fit(X_train_scaled, y_direction_train)
                
                # Predictions
                y_price_pred = self.model['price'].predict(X_test_scaled)
                y_direction_pred = self.model['direction'].predict(X_test_scaled)
                
            elif self.model_type == ModelType.XGBOOST:
                self.model = {
                    'price': xgb.XGBRegressor(random_state=42),
                    'direction': xgb.XGBClassifier(random_state=42)
                }
                self.model['price'].fit(X_train_scaled, y_price_train)
                self.model['direction'].fit(X_train_scaled, y_direction_train)
                
                y_price_pred = self.model['price'].predict(X_test_scaled)
                y_direction_pred = self.model['direction'].predict(X_test_scaled)
                
            elif self.model_type in [ModelType.LSTM, ModelType.GRU]:
                # Reshape for LSTM/GRU (samples, timesteps, features)
                def create_sequences(data, seq_length=60):
                    X_seq, y_seq = [], []
                    for i in range(seq_length, len(data)):
                        X_seq.append(data[i-seq_length:i])
                        y_seq.append(data[i])
                    return np.array(X_seq), np.array(y_seq)
                
                seq_length = min(60, len(X_train_scaled) // 4)
                X_train_seq, y_price_train_seq = create_sequences(X_train_scaled, seq_length)
                X_test_seq, y_price_test_seq = create_sequences(X_test_scaled, seq_length)
                
                # Build neural network
                model = Sequential()
                if self.model_type == ModelType.LSTM:
                    model.add(LSTM(50, return_sequences=True, input_shape=(seq_length, X.shape[1])))
                    model.add(Dropout(0.2))
                    model.add(LSTM(50, return_sequences=False))
                else:  # GRU
                    model.add(GRU(50, return_sequences=True, input_shape=(seq_length, X.shape[1])))
                    model.add(Dropout(0.2))
                    model.add(GRU(50, return_sequences=False))
                
                model.add(Dropout(0.2))
                model.add(Dense(25))
                model.add(Dense(1))
                
                model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
                
                # Train
                early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
                model.fit(
                    X_train_seq, y_price_train_seq,
                    batch_size=32, epochs=50,
                    validation_split=0.1,
                    callbacks=[early_stopping],
                    verbose=0
                )
                
                self.model = {'price': model, 'direction': None}
                y_price_pred = model.predict(X_test_seq).flatten()
                y_direction_pred = (y_price_pred > 0).astype(int)
                
                # Adjust test data to match sequence predictions
                y_price_test = y_price_test_seq
                y_direction_test = y_direction_test[seq_length:]
            
            # Calculate performance metrics
            mse = mean_squared_error(y_price_test, y_price_pred)
            mae = mean_absolute_error(y_price_test, y_price_pred)
            directional_accuracy = accuracy_score(y_direction_test, y_direction_pred)
            
            self.performance_metrics = {
                'mse': mse,
                'mae': mae,
                'directional_accuracy': directional_accuracy,
                'rmse': np.sqrt(mse)
            }
            
            self.is_trained = True
            logger.info(f"Model trained successfully: {self.model_type.value} for {self.symbol}")
            
            return self.performance_metrics
            
        except Exception as e:
            logger.error(f"Failed to train model: {str(e)}")
            raise
    
    def predict(self, features: np.ndarray) -> Dict[str, Any]:
        """Make prediction"""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        try:
            # Scale features
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            if self.model_type in [ModelType.LSTM, ModelType.GRU]:
                # For sequence models, use the last 60 points
                if len(features_scaled[0]) >= 60:
                    features_seq = features_scaled[0][-60:].reshape(1, 60, -1)
                    price_pred = self.model['price'].predict(features_seq)[0][0]
                else:
                    # If not enough data, pad with zeros
                    padded = np.zeros((1, 60, features_scaled.shape[1]))
                    padded[0, -len(features_scaled[0]):] = features_scaled[0]
                    price_pred = self.model['price'].predict(padded)[0][0]
                
                direction_pred = "up" if price_pred > 0 else "down"
                confidence = min(abs(price_pred) * 10, 1.0)  # Simple confidence calculation
                
            else:
                price_pred = self.model['price'].predict(features_scaled)[0]
                direction_proba = self.model['direction'].predict_proba(features_scaled)[0]
                direction_pred = "up" if direction_proba[1] > 0.5 else "down"
                confidence = max(direction_proba)
            
            return {
                'price_change': price_pred,
                'direction': direction_pred,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise
    
    def save_model(self, path: str):
        """Save model to disk"""
        try:
            model_path = Path(path)
            model_path.mkdir(parents=True, exist_ok=True)
            
            # Save model
            if self.model_type in [ModelType.LSTM, ModelType.GRU]:
                self.model['price'].save(model_path / "price_model.h5")
            else:
                joblib.dump(self.model, model_path / "model.pkl")
            
            # Save scaler
            joblib.dump(self.scaler, model_path / "scaler.pkl")
            
            # Save metadata
            metadata = {
                'model_type': self.model_type.value,
                'symbol': self.symbol,
                'timeframe': self.timeframe.value,
                'version': self.version,
                'performance_metrics': self.performance_metrics,
                'is_trained': self.is_trained
            }
            
            joblib.dump(metadata, model_path / "metadata.pkl")
            
            logger.info(f"Model saved to {path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {str(e)}")
            raise
    
    def load_model(self, path: str):
        """Load model from disk"""
        try:
            model_path = Path(path)
            
            # Load metadata
            metadata = joblib.load(model_path / "metadata.pkl")
            self.model_type = ModelType(metadata['model_type'])
            self.symbol = metadata['symbol']
            self.timeframe = PredictionTimeframe(metadata['timeframe'])
            self.version = metadata['version']
            self.performance_metrics = metadata['performance_metrics']
            self.is_trained = metadata['is_trained']
            
            # Load scaler
            self.scaler = joblib.load(model_path / "scaler.pkl")
            
            # Load model
            if self.model_type in [ModelType.LSTM, ModelType.GRU]:
                price_model = keras_load_model(model_path / "price_model.h5")
                self.model = {'price': price_model, 'direction': None}
            else:
                self.model = joblib.load(model_path / "model.pkl")
            
            logger.info(f"Model loaded from {path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

class MLEngine:
    def __init__(self):
        self.models: Dict[str, MLModel] = {}
        # Get project root directory
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        self.model_dir = project_root / "models"
        self.model_dir.mkdir(exist_ok=True)
        
    async def initialize(self):
        """Initialize the ML engine"""
        logger.info("Initializing ML Engine")
        await self.load_models()
        
    async def shutdown(self):
        """Shutdown the ML engine"""
        logger.info("Shutting down ML Engine")
        
    async def load_models(self):
        """Load existing models from disk"""
        try:
            for model_path in self.model_dir.iterdir():
                if model_path.is_dir():
                    try:
                        model = MLModel(ModelType.RANDOM_FOREST, "", PredictionTimeframe.INTRADAY)
                        model.load_model(str(model_path))
                        
                        model_key = f"{model.symbol}_{model.timeframe.value}_{model.model_type.value}"
                        self.models[model_key] = model
                        
                        logger.info(f"Loaded model: {model_key}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to load model from {model_path}: {str(e)}")
                        
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
    
    async def train_model(
        self, 
        symbol: str, 
        timeframe: PredictionTimeframe, 
        model_type: ModelType, 
        data: pd.DataFrame
    ) -> ModelPerformance:
        """Train a new model"""
        try:
            model = MLModel(model_type, symbol, timeframe)
            performance_metrics = model.train(data)
            
            # Save model
            model_key = f"{symbol}_{timeframe.value}_{model_type.value}"
            model_path = self.model_dir / model_key
            model.save_model(str(model_path))
            
            # Store in memory
            self.models[model_key] = model
            
            logger.info(f"Model trained and saved: {model_key}")
            
            return ModelPerformance(
                model_name=model_key,
                model_version=model.version,
                accuracy=performance_metrics.get('directional_accuracy', 0),
                precision=0,  # TODO: Calculate precision
                recall=0,     # TODO: Calculate recall
                f1_score=0,   # TODO: Calculate F1 score
                mse=performance_metrics.get('mse', 0),
                mae=performance_metrics.get('mae', 0),
                directional_accuracy=performance_metrics.get('directional_accuracy', 0)
            )
            
        except Exception as e:
            logger.error(f"Failed to train model: {str(e)}")
            raise
    
    async def predict(self, request: PredictionRequest) -> PredictionResult:
        """Generate prediction"""
        try:
            # Find best model for symbol and timeframe
            model_candidates = [
                f"{request.symbol}_{request.timeframe.value}_{model_type.value}"
                for model_type in ModelType
            ]
            
            best_model = None
            best_performance = 0
            
            for model_key in model_candidates:
                if model_key in self.models:
                    model = self.models[model_key]
                    accuracy = model.performance_metrics.get('directional_accuracy', 0)
                    if accuracy > best_performance:
                        best_model = model
                        best_performance = accuracy
            
            if not best_model:
                raise ValueError(f"No trained model found for {request.symbol} {request.timeframe.value}")
            
            # Get current market data from data service
            import httpx
            async with httpx.AsyncClient() as client:
                try:
                    # Get real-time price from data service
                    price_response = await client.get(
                        f"http://localhost:8002/v1/market-data/{request.symbol}/current",
                        timeout=10.0
                    )
                    if price_response.status_code == 200:
                        price_data = price_response.json()
                        current_price = price_data['current_price']
                    else:
                        raise ValueError(f"Failed to get current price: {price_response.status_code}")
                    
                    # Get historical data for feature engineering
                    history_response = await client.get(
                        f"http://localhost:8002/v1/market-data/{request.symbol}/history",
                        params={"period": "1mo", "interval": "1d"},
                        timeout=15.0
                    )
                    if history_response.status_code == 200:
                        history_data = history_response.json()
                        df = pd.DataFrame(history_data['data'])
                        
                        # Prepare latest features from real data
                        X, _, _ = best_model.prepare_features(df)
                        features = X[-1]  # Use latest feature vector
                    else:
                        raise ValueError(f"Failed to get historical data: {history_response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Failed to get real market data: {e}")
                    # Fallback to last known data or raise error
                    raise ValueError(f"Unable to get market data for prediction: {e}")
            
            # Make prediction
            prediction = best_model.predict(features)
            
            # Calculate predicted price
            predicted_price = current_price * (1 + prediction['price_change'])
            
            return PredictionResult(
                symbol=request.symbol,
                predicted_price=predicted_price,
                current_price=current_price,
                predicted_direction=prediction['direction'],
                confidence_score=prediction['confidence'],
                model_version=best_model.version,
                features_used=['technical_indicators', 'volume_analysis'],
                prediction_horizon=request.horizon,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise
    
    async def get_model_performance(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Get model performance metrics"""
        try:
            performance_data = {}
            
            for model_type in ModelType:
                model_key = f"{symbol}_{timeframe}_{model_type.value}"
                if model_key in self.models:
                    model = self.models[model_key]
                    performance_data[model_type.value] = model.performance_metrics
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Failed to get model performance: {str(e)}")
            raise
    
    async def retrain_models(self):
        """Retrain all models with new data"""
        # TODO: Implement model retraining
        logger.info("Model retraining not yet implemented")

# Singleton instance
ml_engine = MLEngine()