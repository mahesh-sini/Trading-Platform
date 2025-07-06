import pytest
import asyncio
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from ml_service.services.ml_engine import MLEngine, MLModel
from ml_service.services.prediction_service import prediction_service
from ml_service.services.feature_engineering import feature_engineering_service

class TestMLEngine:
    """Test cases for ML Engine"""

    @pytest.fixture
    def ml_engine(self):
        return MLEngine()

    @pytest.fixture
    def sample_data(self):
        """Sample market data for testing"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(100, 200, 100),
            'low': np.random.uniform(100, 200, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.randint(1000000, 10000000, 100)
        })
        return data

    def test_ml_model_initialization(self):
        """Test ML model initialization"""
        model = MLModel(
            symbol="AAPL",
            model_type="lstm",
            features=["close", "volume", "sma_20"],
            target="close",
            lookback_window=20
        )
        
        assert model.symbol == "AAPL"
        assert model.model_type == "lstm"
        assert len(model.features) == 3
        assert model.target == "close"
        assert model.lookback_window == 20
        assert model.model is None  # Not trained yet

    def test_prepare_features(self, sample_data):
        """Test feature preparation"""
        model = MLModel(
            symbol="AAPL",
            model_type="lstm",
            features=["close", "volume"],
            target="close",
            lookback_window=20
        )
        
        X, y = model.prepare_features(sample_data)
        
        assert X is not None
        assert y is not None
        assert len(X) == len(y)
        assert len(X) <= len(sample_data) - model.lookback_window

    def test_train_lstm_model(self, sample_data):
        """Test LSTM model training"""
        model = MLModel(
            symbol="AAPL",
            model_type="lstm",
            features=["close", "volume"],
            target="close",
            lookback_window=20
        )
        
        # Mock tensorflow to avoid heavy computation in tests
        with patch('tensorflow.keras.Sequential') as mock_sequential:
            mock_model = MagicMock()
            mock_sequential.return_value = mock_model
            
            success = model.train(sample_data)
            
            assert success
            assert model.model is not None
            mock_model.fit.assert_called_once()

    def test_train_random_forest_model(self, sample_data):
        """Test Random Forest model training"""
        model = MLModel(
            symbol="AAPL",
            model_type="random_forest",
            features=["close", "volume"],
            target="close",
            lookback_window=20
        )
        
        success = model.train(sample_data)
        
        assert success
        assert model.model is not None

    def test_predict_success(self, sample_data):
        """Test successful prediction"""
        model = MLModel(
            symbol="AAPL",
            model_type="random_forest",
            features=["close", "volume"],
            target="close",
            lookback_window=20
        )
        
        # Train the model first
        model.train(sample_data)
        
        # Make prediction
        prediction = model.predict(sample_data.tail(20))
        
        assert prediction is not None
        assert isinstance(prediction, (int, float, np.number))

    def test_predict_without_training(self, sample_data):
        """Test prediction without training"""
        model = MLModel(
            symbol="AAPL",
            model_type="random_forest",
            features=["close", "volume"],
            target="close",
            lookback_window=20
        )
        
        prediction = model.predict(sample_data.tail(20))
        
        assert prediction is None

    def test_model_evaluation(self, sample_data):
        """Test model evaluation"""
        model = MLModel(
            symbol="AAPL",
            model_type="random_forest",
            features=["close", "volume"],
            target="close",
            lookback_window=20
        )
        
        # Train the model
        model.train(sample_data)
        
        # Evaluate
        metrics = model.evaluate(sample_data)
        
        assert metrics is not None
        assert "mse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics

class TestPredictionService:
    """Test cases for Prediction Service"""

    @pytest.mark.asyncio
    async def test_generate_prediction_success(self, mock_ml_service):
        """Test successful prediction generation"""
        symbol = "AAPL"
        prediction_type = "price"
        horizon = "1d"
        
        result = await prediction_service.generate_prediction(symbol, prediction_type, horizon)
        
        assert result is not None
        assert "predicted_price" in result
        assert "confidence" in result
        assert result["symbol"] == symbol

    @pytest.mark.asyncio
    async def test_generate_prediction_invalid_symbol(self):
        """Test prediction with invalid symbol"""
        with patch('ml_service.services.data_service.get_historical_data') as mock_data:
            mock_data.return_value = pd.DataFrame()  # Empty data
            
            result = await prediction_service.generate_prediction("INVALID", "price", "1d")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_model_performance(self):
        """Test getting model performance"""
        symbol = "AAPL"
        model_type = "lstm"
        
        with patch.object(prediction_service, 'models') as mock_models:
            mock_model = MagicMock()
            mock_model.get_performance_metrics.return_value = {
                "accuracy": 0.85,
                "mse": 0.1,
                "mae": 0.05
            }
            mock_models.get.return_value = mock_model
            
            performance = await prediction_service.get_model_performance(symbol, model_type)
            
            assert performance is not None
            assert "accuracy" in performance

    @pytest.mark.asyncio
    async def test_retrain_model_success(self):
        """Test successful model retraining"""
        symbol = "AAPL"
        model_type = "lstm"
        
        with patch.object(prediction_service, '_train_model') as mock_train:
            mock_train.return_value = True
            
            success = await prediction_service.retrain_model(symbol, model_type)
            
            assert success

    @pytest.mark.asyncio
    async def test_update_model_features(self):
        """Test updating model features"""
        symbol = "AAPL"
        model_type = "lstm"
        new_features = ["close", "volume", "sma_20", "rsi"]
        
        success = await prediction_service.update_model_features(symbol, model_type, new_features)
        
        assert success is not None

class TestFeatureEngineering:
    """Test cases for Feature Engineering Service"""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Sample OHLCV data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(100, 200, 100),
            'low': np.random.uniform(100, 200, 100),
            'close': np.random.uniform(100, 200, 100),
            'volume': np.random.randint(1000000, 10000000, 100)
        })
        # Ensure high >= low and close is within range
        data['high'] = np.maximum(data[['open', 'close']].max(axis=1), data['high'])
        data['low'] = np.minimum(data[['open', 'close']].min(axis=1), data['low'])
        return data

    def test_calculate_sma(self, sample_ohlcv_data):
        """Test Simple Moving Average calculation"""
        result = feature_engineering_service.calculate_sma(sample_ohlcv_data, 'close', 20)
        
        assert 'sma_20' in result.columns
        assert not result['sma_20'].iloc[19:].isna().all()  # Should have values after window

    def test_calculate_ema(self, sample_ohlcv_data):
        """Test Exponential Moving Average calculation"""
        result = feature_engineering_service.calculate_ema(sample_ohlcv_data, 'close', 20)
        
        assert 'ema_20' in result.columns
        assert not result['ema_20'].isna().all()

    def test_calculate_rsi(self, sample_ohlcv_data):
        """Test RSI calculation"""
        result = feature_engineering_service.calculate_rsi(sample_ohlcv_data, 'close', 14)
        
        assert 'rsi_14' in result.columns
        rsi_values = result['rsi_14'].dropna()
        assert (rsi_values >= 0).all()
        assert (rsi_values <= 100).all()

    def test_calculate_macd(self, sample_ohlcv_data):
        """Test MACD calculation"""
        result = feature_engineering_service.calculate_macd(sample_ohlcv_data, 'close')
        
        assert 'macd' in result.columns
        assert 'macd_signal' in result.columns
        assert 'macd_histogram' in result.columns

    def test_calculate_bollinger_bands(self, sample_ohlcv_data):
        """Test Bollinger Bands calculation"""
        result = feature_engineering_service.calculate_bollinger_bands(sample_ohlcv_data, 'close', 20, 2)
        
        assert 'bb_upper' in result.columns
        assert 'bb_middle' in result.columns
        assert 'bb_lower' in result.columns
        
        # Upper should be >= middle >= lower
        valid_data = result.dropna()
        if not valid_data.empty:
            assert (valid_data['bb_upper'] >= valid_data['bb_middle']).all()
            assert (valid_data['bb_middle'] >= valid_data['bb_lower']).all()

    def test_calculate_volume_indicators(self, sample_ohlcv_data):
        """Test volume indicators calculation"""
        result = feature_engineering_service.calculate_volume_indicators(sample_ohlcv_data)
        
        assert 'volume_sma' in result.columns
        assert 'volume_ratio' in result.columns

    def test_add_all_features(self, sample_ohlcv_data):
        """Test adding all features at once"""
        result = feature_engineering_service.add_all_features(sample_ohlcv_data)
        
        # Check that multiple features were added
        expected_features = ['sma_20', 'ema_20', 'rsi_14', 'macd', 'bb_upper', 'volume_sma']
        for feature in expected_features:
            assert feature in result.columns

    def test_normalize_features(self, sample_ohlcv_data):
        """Test feature normalization"""
        # Add some features first
        data_with_features = feature_engineering_service.add_all_features(sample_ohlcv_data)
        
        features_to_normalize = ['close', 'volume', 'sma_20']
        result = feature_engineering_service.normalize_features(data_with_features, features_to_normalize)
        
        for feature in features_to_normalize:
            if feature in result.columns:
                normalized_values = result[feature].dropna()
                if not normalized_values.empty:
                    # Values should be roughly between -3 and 3 for z-score normalization
                    assert normalized_values.abs().max() <= 10  # Allow some outliers

    def test_create_lagged_features(self, sample_ohlcv_data):
        """Test lagged features creation"""
        features = ['close', 'volume']
        lags = [1, 2, 3]
        
        result = feature_engineering_service.create_lagged_features(sample_ohlcv_data, features, lags)
        
        for feature in features:
            for lag in lags:
                lag_col = f"{feature}_lag_{lag}"
                assert lag_col in result.columns