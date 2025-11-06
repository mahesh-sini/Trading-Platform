from sqlalchemy import Column, String, Float, Integer, DateTime, Enum as SQLEnum, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import BaseModel
import enum
from datetime import datetime


class PredictionDirection(str, enum.Enum):
    """Prediction direction enumeration"""
    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class PredictionTimeframe(str, enum.Enum):
    """Prediction timeframe enumeration"""
    INTRADAY = "intraday"
    SHORT_TERM = "short_term"  # 1-5 days
    MEDIUM_TERM = "medium_term"  # 1-4 weeks
    LONG_TERM = "long_term"  # 1-3 months


class ModelType(str, enum.Enum):
    """Model type enumeration"""
    LSTM = "lstm"
    GRU = "gru"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    ENSEMBLE = "ensemble"
    TRANSFORMER = "transformer"


class Prediction(BaseModel):
    """ML prediction model"""
    __tablename__ = "predictions"

    # Symbol
    symbol = Column(String(20), nullable=False, index=True)

    # Prediction details
    predicted_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    predicted_change_percent = Column(Float, nullable=False)
    direction = Column(SQLEnum(PredictionDirection), nullable=False, index=True)

    # Timeframe
    timeframe = Column(SQLEnum(PredictionTimeframe), nullable=False, index=True)
    prediction_horizon_days = Column(Integer, nullable=False)
    target_date = Column(DateTime, nullable=False, index=True)

    # Confidence and probability
    confidence_score = Column(Float, nullable=False)  # 0-1 scale
    probability_up = Column(Float, nullable=True)
    probability_down = Column(Float, nullable=True)

    # Model information
    model_type = Column(SQLEnum(ModelType), nullable=False)
    model_id = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)

    # Feature importance (top features that influenced prediction)
    feature_importance = Column(JSON, nullable=True)

    # Technical indicators at prediction time
    technical_indicators = Column(JSON, nullable=True)

    # Validation
    actual_price = Column(Float, nullable=True)
    actual_change_percent = Column(Float, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    prediction_error = Column(Float, nullable=True)

    # Status
    is_validated = Column(Boolean, default=False, nullable=False)
    validated_at = Column(DateTime, nullable=True)

    # User reference (optional - can be system-generated)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Metadata
    prediction_metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Prediction(symbol={self.symbol}, direction={self.direction}, confidence={self.confidence_score})>"

    @property
    def expected_return(self):
        """Calculate expected return percentage"""
        return self.predicted_change_percent

    @property
    def days_until_target(self):
        """Get days until target date"""
        delta = self.target_date - datetime.utcnow()
        return max(0, delta.days)

    def validate(self, actual_price: float):
        """Validate prediction against actual price"""
        self.actual_price = actual_price
        self.actual_change_percent = ((actual_price - self.current_price) / self.current_price) * 100

        # Check if direction was correct
        predicted_direction_up = self.direction == PredictionDirection.UP
        actual_direction_up = self.actual_change_percent > 0

        self.is_correct = predicted_direction_up == actual_direction_up

        # Calculate prediction error
        self.prediction_error = abs(self.predicted_price - actual_price) / actual_price

        self.is_validated = True
        self.validated_at = datetime.utcnow()


class ModelPerformance(BaseModel):
    """ML model performance tracking"""
    __tablename__ = "model_performance"

    # Model information
    model_id = Column(String(100), nullable=False, index=True)
    model_version = Column(String(50), nullable=False)
    model_type = Column(SQLEnum(ModelType), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)

    # Training information
    trained_at = Column(DateTime, nullable=False)
    training_samples = Column(Integer, nullable=False)
    validation_samples = Column(Integer, nullable=True)

    # Training metrics
    training_loss = Column(Float, nullable=True)
    validation_loss = Column(Float, nullable=True)
    training_accuracy = Column(Float, nullable=True)
    validation_accuracy = Column(Float, nullable=True)

    # Performance metrics
    total_predictions = Column(Integer, default=0, nullable=False)
    correct_predictions = Column(Integer, default=0, nullable=False)
    accuracy = Column(Float, default=0.0, nullable=False)

    # Direction accuracy
    up_predictions = Column(Integer, default=0, nullable=False)
    down_predictions = Column(Integer, default=0, nullable=False)
    up_correct = Column(Integer, default=0, nullable=False)
    down_correct = Column(Integer, default=0, nullable=False)

    # Error metrics
    mean_absolute_error = Column(Float, nullable=True)
    mean_squared_error = Column(Float, nullable=True)
    root_mean_squared_error = Column(Float, nullable=True)
    mean_absolute_percentage_error = Column(Float, nullable=True)

    # Financial metrics
    avg_predicted_return = Column(Float, nullable=True)
    avg_actual_return = Column(Float, nullable=True)
    return_correlation = Column(Float, nullable=True)

    # By timeframe
    intraday_accuracy = Column(Float, nullable=True)
    short_term_accuracy = Column(Float, nullable=True)
    medium_term_accuracy = Column(Float, nullable=True)
    long_term_accuracy = Column(Float, nullable=True)

    # Confidence calibration
    avg_confidence = Column(Float, nullable=True)
    confidence_accuracy_correlation = Column(Float, nullable=True)

    # Model configuration
    hyperparameters = Column(JSON, nullable=True)
    features_used = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_production = Column(Boolean, default=False, nullable=False)

    # Last update
    last_evaluated_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ModelPerformance(model={self.model_name}, accuracy={self.accuracy}, predictions={self.total_predictions})>"

    def update_metrics(self):
        """Update performance metrics"""
        if self.total_predictions > 0:
            self.accuracy = (self.correct_predictions / self.total_predictions) * 100

        if self.up_predictions > 0:
            up_accuracy = (self.up_correct / self.up_predictions) * 100
        else:
            up_accuracy = 0.0

        if self.down_predictions > 0:
            down_accuracy = (self.down_correct / self.down_predictions) * 100
        else:
            down_accuracy = 0.0

        self.last_evaluated_at = datetime.utcnow()
