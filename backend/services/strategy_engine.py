import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from models.strategy import Strategy, StrategyType
from models.trade import Trade, Position
from services.risk_management import risk_manager
from services.broker_service import trading_service as broker_service
from services.database import get_db

logger = logging.getLogger(__name__)

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class TradingSignal:
    signal: SignalType
    symbol: str
    confidence: float
    price: float
    quantity: int
    reason: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, strategy_id: str, parameters: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.parameters = parameters
        self.is_active = False
        self.positions = {}
        self.performance_metrics = {}
        
    @abstractmethod
    async def generate_signal(self, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate trading signal based on market data"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> int:
        """Calculate position size for the signal"""
        pass
    
    async def execute_signal(self, signal: TradingSignal) -> bool:
        """Execute trading signal"""
        try:
            # Risk management check
            risk_assessment = await risk_manager.assess_order_risk({
                "symbol": signal.symbol,
                "side": signal.signal.value,
                "quantity": signal.quantity,
                "price": signal.price
            })
            
            if risk_assessment["risk_score"] > 0.8:
                logger.warning(f"High risk signal rejected: {signal}")
                return False
            
            # Execute order through broker
            order_result = await broker_service.place_order({
                "symbol": signal.symbol,
                "side": signal.signal.value,
                "type": "market",
                "quantity": signal.quantity
            })
            
            if order_result["status"] == "success":
                logger.info(f"Signal executed successfully: {signal}")
                await self._update_position(signal)
                return True
            else:
                logger.error(f"Failed to execute signal: {signal}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing signal {signal}: {str(e)}")
            return False
    
    async def _update_position(self, signal: TradingSignal):
        """Update position tracking"""
        if signal.symbol not in self.positions:
            self.positions[signal.symbol] = {
                "quantity": 0,
                "average_price": 0,
                "realized_pnl": 0
            }
        
        position = self.positions[signal.symbol]
        
        if signal.signal == SignalType.BUY:
            old_quantity = position["quantity"]
            old_avg_price = position["average_price"]
            new_quantity = old_quantity + signal.quantity
            
            # Calculate new average price
            if new_quantity > 0:
                position["average_price"] = (
                    (old_quantity * old_avg_price + signal.quantity * signal.price) / new_quantity
                )
            position["quantity"] = new_quantity
            
        elif signal.signal == SignalType.SELL:
            position["quantity"] -= signal.quantity
            # Calculate realized PnL
            realized_pnl = signal.quantity * (signal.price - position["average_price"])
            position["realized_pnl"] += realized_pnl

class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy"""
    
    def __init__(self, strategy_id: str, parameters: Dict[str, Any] = None):
        default_params = {
            "lookback_period": 20,
            "momentum_threshold": 0.02,
            "stop_loss": 0.05,
            "take_profit": 0.10,
            "max_position_size": 0.05
        }
        params = {**default_params, **(parameters or {})}
        super().__init__(strategy_id, params)
        
    async def generate_signal(self, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate momentum-based signal"""
        try:
            symbol = market_data["symbol"]
            prices = market_data["prices"]  # List of recent prices
            
            if len(prices) < self.parameters["lookback_period"]:
                return None
            
            # Calculate momentum
            current_price = prices[-1]
            past_price = prices[-self.parameters["lookback_period"]]
            momentum = (current_price - past_price) / past_price
            
            # Generate signal based on momentum
            if momentum > self.parameters["momentum_threshold"]:
                return TradingSignal(
                    signal=SignalType.BUY,
                    symbol=symbol,
                    confidence=min(momentum * 5, 1.0),  # Scale confidence
                    price=current_price,
                    quantity=0,  # Will be calculated by position sizing
                    reason=f"Strong momentum: {momentum:.3f}",
                    timestamp=datetime.now(),
                    metadata={"momentum": momentum}
                )
            elif momentum < -self.parameters["momentum_threshold"]:
                return TradingSignal(
                    signal=SignalType.SELL,
                    symbol=symbol,
                    confidence=min(abs(momentum) * 5, 1.0),
                    price=current_price,
                    quantity=0,
                    reason=f"Negative momentum: {momentum:.3f}",
                    timestamp=datetime.now(),
                    metadata={"momentum": momentum}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating momentum signal: {str(e)}")
            return None
    
    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> int:
        """Calculate position size based on risk and confidence"""
        max_position_value = portfolio_value * self.parameters["max_position_size"]
        base_quantity = int(max_position_value / signal.price)
        
        # Adjust based on confidence
        adjusted_quantity = int(base_quantity * signal.confidence)
        
        return max(1, adjusted_quantity)

class MeanReversionStrategy(BaseStrategy):
    """Mean reversion trading strategy"""
    
    def __init__(self, strategy_id: str, parameters: Dict[str, Any] = None):
        default_params = {
            "lookback_period": 20,
            "bollinger_std": 2.0,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "max_position_size": 0.03
        }
        params = {**default_params, **(parameters or {})}
        super().__init__(strategy_id, params)
    
    async def generate_signal(self, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate mean reversion signal"""
        try:
            symbol = market_data["symbol"]
            prices = market_data["prices"]
            
            if len(prices) < self.parameters["lookback_period"]:
                return None
            
            # Calculate indicators
            df = pd.DataFrame({"price": prices})
            
            # Bollinger Bands
            sma = df["price"].rolling(self.parameters["lookback_period"]).mean()
            std = df["price"].rolling(self.parameters["lookback_period"]).std()
            upper_band = sma + (std * self.parameters["bollinger_std"])
            lower_band = sma - (std * self.parameters["bollinger_std"])
            
            # RSI
            delta = df["price"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            current_price = prices[-1]
            current_rsi = rsi.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            
            # Generate signals
            if (current_price < current_lower and 
                current_rsi < self.parameters["rsi_oversold"]):
                
                confidence = (self.parameters["rsi_oversold"] - current_rsi) / 100
                return TradingSignal(
                    signal=SignalType.BUY,
                    symbol=symbol,
                    confidence=confidence,
                    price=current_price,
                    quantity=0,
                    reason=f"Oversold: RSI={current_rsi:.1f}, Below lower band",
                    timestamp=datetime.now(),
                    metadata={"rsi": current_rsi, "lower_band": current_lower}
                )
                
            elif (current_price > current_upper and 
                  current_rsi > self.parameters["rsi_overbought"]):
                
                confidence = (current_rsi - self.parameters["rsi_overbought"]) / 100
                return TradingSignal(
                    signal=SignalType.SELL,
                    symbol=symbol,
                    confidence=confidence,
                    price=current_price,
                    quantity=0,
                    reason=f"Overbought: RSI={current_rsi:.1f}, Above upper band",
                    timestamp=datetime.now(),
                    metadata={"rsi": current_rsi, "upper_band": current_upper}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating mean reversion signal: {str(e)}")
            return None
    
    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> int:
        """Calculate position size for mean reversion"""
        max_position_value = portfolio_value * self.parameters["max_position_size"]
        base_quantity = int(max_position_value / signal.price)
        
        # Conservative sizing for mean reversion
        adjusted_quantity = int(base_quantity * signal.confidence * 0.8)
        
        return max(1, adjusted_quantity)

class MLBasedStrategy(BaseStrategy):
    """Machine learning based trading strategy"""
    
    def __init__(self, strategy_id: str, parameters: Dict[str, Any] = None):
        default_params = {
            "model_confidence_threshold": 0.6,
            "prediction_horizon": "1d",
            "max_position_size": 0.04,
            "feature_importance_threshold": 0.1
        }
        params = {**default_params, **(parameters or {})}
        super().__init__(strategy_id, params)
    
    async def generate_signal(self, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Generate ML-based signal"""
        try:
            symbol = market_data["symbol"]
            
            # Get ML prediction from ML service
            prediction_data = await self._get_ml_prediction(symbol)
            
            if not prediction_data or prediction_data["confidence"] < self.parameters["model_confidence_threshold"]:
                return None
            
            current_price = market_data["current_price"]
            predicted_price = prediction_data["predicted_price"]
            confidence = prediction_data["confidence"]
            
            # Calculate expected return
            expected_return = (predicted_price - current_price) / current_price
            
            # Generate signal based on prediction
            if expected_return > 0.02:  # 2% expected return threshold
                return TradingSignal(
                    signal=SignalType.BUY,
                    symbol=symbol,
                    confidence=confidence,
                    price=current_price,
                    quantity=0,
                    reason=f"ML Prediction: {predicted_price:.2f} (confidence: {confidence:.2f})",
                    timestamp=datetime.now(),
                    metadata={
                        "predicted_price": predicted_price,
                        "expected_return": expected_return,
                        "model_confidence": confidence
                    }
                )
            elif expected_return < -0.02:  # -2% expected return threshold
                return TradingSignal(
                    signal=SignalType.SELL,
                    symbol=symbol,
                    confidence=confidence,
                    price=current_price,
                    quantity=0,
                    reason=f"ML Prediction: {predicted_price:.2f} (confidence: {confidence:.2f})",
                    timestamp=datetime.now(),
                    metadata={
                        "predicted_price": predicted_price,
                        "expected_return": expected_return,
                        "model_confidence": confidence
                    }
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating ML signal: {str(e)}")
            return None
    
    async def _get_ml_prediction(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ML prediction from ML service"""
        try:
            # This would integrate with the ML service
            # For now, return mock data
            return {
                "predicted_price": 150.0,
                "confidence": 0.75,
                "features_used": ["sma_20", "rsi", "volume"]
            }
        except Exception as e:
            logger.error(f"Error getting ML prediction: {str(e)}")
            return None
    
    def calculate_position_size(self, signal: TradingSignal, portfolio_value: float) -> int:
        """Calculate position size based on ML confidence"""
        max_position_value = portfolio_value * self.parameters["max_position_size"]
        base_quantity = int(max_position_value / signal.price)
        
        # Size based on model confidence and expected return
        expected_return = abs(signal.metadata.get("expected_return", 0))
        confidence_multiplier = signal.confidence * min(expected_return * 10, 1.0)
        
        adjusted_quantity = int(base_quantity * confidence_multiplier)
        
        return max(1, adjusted_quantity)

class StrategyEngine:
    """Main strategy engine that manages and executes trading strategies"""
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategies: List[str] = []
        self.strategy_performance: Dict[str, Dict] = {}
        
    def register_strategy(self, strategy: BaseStrategy):
        """Register a new strategy"""
        self.strategies[strategy.strategy_id] = strategy
        logger.info(f"Strategy registered: {strategy.strategy_id}")
    
    def activate_strategy(self, strategy_id: str):
        """Activate a strategy"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].is_active = True
            if strategy_id not in self.active_strategies:
                self.active_strategies.append(strategy_id)
            logger.info(f"Strategy activated: {strategy_id}")
    
    def deactivate_strategy(self, strategy_id: str):
        """Deactivate a strategy"""
        if strategy_id in self.strategies:
            self.strategies[strategy_id].is_active = False
            if strategy_id in self.active_strategies:
                self.active_strategies.remove(strategy_id)
            logger.info(f"Strategy deactivated: {strategy_id}")
    
    async def process_market_data(self, market_data: Dict[str, Any]):
        """Process market data and generate signals from active strategies"""
        signals = []
        
        for strategy_id in self.active_strategies:
            strategy = self.strategies[strategy_id]
            
            try:
                signal = await strategy.generate_signal(market_data)
                if signal:
                    # Calculate position size
                    portfolio_value = await self._get_portfolio_value()
                    signal.quantity = strategy.calculate_position_size(signal, portfolio_value)
                    
                    signals.append(signal)
                    logger.info(f"Signal generated by {strategy_id}: {signal}")
                    
            except Exception as e:
                logger.error(f"Error processing market data for strategy {strategy_id}: {str(e)}")
        
        return signals
    
    async def execute_signals(self, signals: List[TradingSignal]):
        """Execute list of trading signals"""
        executed_signals = []
        
        for signal in signals:
            try:
                # Find strategy that generated the signal
                strategy = None
                for s in self.strategies.values():
                    if s.is_active:
                        strategy = s
                        break
                
                if strategy:
                    success = await strategy.execute_signal(signal)
                    if success:
                        executed_signals.append(signal)
                        await self._update_strategy_performance(strategy.strategy_id, signal)
                        
            except Exception as e:
                logger.error(f"Error executing signal {signal}: {str(e)}")
        
        return executed_signals
    
    async def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        try:
            # This would integrate with portfolio service
            return 100000.0  # Mock value
        except Exception as e:
            logger.error(f"Error getting portfolio value: {str(e)}")
            return 100000.0
    
    async def _update_strategy_performance(self, strategy_id: str, signal: TradingSignal):
        """Update strategy performance metrics"""
        try:
            if strategy_id not in self.strategy_performance:
                self.strategy_performance[strategy_id] = {
                    "total_signals": 0,
                    "executed_signals": 0,
                    "total_return": 0.0,
                    "win_rate": 0.0,
                    "avg_confidence": 0.0
                }
            
            perf = self.strategy_performance[strategy_id]
            perf["total_signals"] += 1
            perf["executed_signals"] += 1
            perf["avg_confidence"] = (
                (perf["avg_confidence"] * (perf["total_signals"] - 1) + signal.confidence) 
                / perf["total_signals"]
            )
            
        except Exception as e:
            logger.error(f"Error updating strategy performance: {str(e)}")
    
    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """Get performance metrics for a strategy"""
        return self.strategy_performance.get(strategy_id, {})
    
    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all strategies"""
        result = {}
        for strategy_id, strategy in self.strategies.items():
            result[strategy_id] = {
                "type": strategy.__class__.__name__,
                "is_active": strategy.is_active,
                "parameters": strategy.parameters,
                "performance": self.get_strategy_performance(strategy_id)
            }
        return result

# Global strategy engine instance
strategy_engine = StrategyEngine()

# Initialize default strategies
def initialize_default_strategies():
    """Initialize default trading strategies"""
    
    # Momentum strategy
    momentum_strategy = MomentumStrategy("momentum_default")
    strategy_engine.register_strategy(momentum_strategy)
    
    # Mean reversion strategy
    mean_reversion_strategy = MeanReversionStrategy("mean_reversion_default")
    strategy_engine.register_strategy(mean_reversion_strategy)
    
    # ML-based strategy
    ml_strategy = MLBasedStrategy("ml_default")
    strategy_engine.register_strategy(ml_strategy)
    
    logger.info("Default strategies initialized")

# Initialize on module load
initialize_default_strategies()