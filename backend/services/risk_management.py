from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskMetrics:
    portfolio_value: float
    total_exposure: float
    leverage_ratio: float
    concentration_risk: float
    sector_concentration: Dict[str, float]
    daily_var: float  # Value at Risk
    max_drawdown: float
    sharpe_ratio: float
    beta: float

@dataclass
class PositionSizing:
    recommended_quantity: int
    max_quantity: int
    risk_amount: float
    position_value: float
    portfolio_percentage: float

@dataclass
class RiskAssessment:
    risk_level: RiskLevel
    risk_score: float  # 0-100
    warnings: List[str]
    recommendations: List[str]
    max_position_size: float
    stop_loss_price: Optional[float]
    take_profit_price: Optional[float]

class RiskManager:
    def __init__(self):
        self.max_position_size = 0.10  # 10% of portfolio
        self.max_portfolio_risk = 0.02  # 2% risk per trade
        self.max_daily_loss = 0.05  # 5% daily loss limit
        self.max_sector_concentration = 0.30  # 30% per sector
        self.max_correlation = 0.70  # Maximum correlation between positions
        self.max_leverage = 2.0  # 2:1 leverage limit
        
    async def assess_trade_risk(
        self,
        symbol: str,
        quantity: int,
        price: float,
        side: str,
        portfolio_value: float,
        current_positions: List[Dict],
        market_data: Optional[Dict] = None
    ) -> RiskAssessment:
        """Comprehensive risk assessment for a potential trade"""
        
        warnings = []
        recommendations = []
        risk_factors = []
        
        # Calculate position value and portfolio percentage
        position_value = quantity * price
        portfolio_percentage = position_value / portfolio_value
        
        # Position size risk
        if portfolio_percentage > self.max_position_size:
            risk_factors.append(50)  # High risk
            warnings.append(f"Position size ({portfolio_percentage:.1%}) exceeds maximum allowed ({self.max_position_size:.1%})")
            recommendations.append(f"Reduce quantity to max {int(portfolio_value * self.max_position_size / price)} shares")
        elif portfolio_percentage > self.max_position_size * 0.8:
            risk_factors.append(30)  # Medium risk
            warnings.append(f"Position size ({portfolio_percentage:.1%}) is approaching maximum limit")
        
        # Concentration risk
        total_exposure = self._calculate_total_exposure(current_positions, symbol, position_value)
        if total_exposure > self.max_portfolio_risk * portfolio_value:
            risk_factors.append(40)
            warnings.append(f"Total exposure to {symbol} exceeds risk limits")
        
        # Sector concentration (if market data available)
        if market_data and market_data.get("sector"):
            sector_risk = self._assess_sector_concentration(
                current_positions, market_data["sector"], position_value, portfolio_value
            )
            if sector_risk > 0:
                risk_factors.append(sector_risk)
                if sector_risk > 30:
                    warnings.append(f"High concentration in {market_data['sector']} sector")
        
        # Volatility risk
        if market_data and market_data.get("volatility"):
            volatility = market_data["volatility"]
            if volatility > 0.5:  # 50% annualized volatility
                risk_factors.append(35)
                warnings.append(f"High volatility ({volatility:.1%}) detected")
                recommendations.append("Consider reducing position size due to high volatility")
        
        # Calculate overall risk score
        risk_score = min(100, sum(risk_factors))
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 50:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 30:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        # Calculate optimal position sizing
        optimal_sizing = self._calculate_position_sizing(
            symbol, price, portfolio_value, market_data
        )
        
        # Calculate stop loss and take profit
        stop_loss, take_profit = self._calculate_risk_levels(
            price, side, market_data
        )
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            warnings=warnings,
            recommendations=recommendations,
            max_position_size=optimal_sizing.max_quantity,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit
        )
    
    def _calculate_total_exposure(self, positions: List[Dict], symbol: str, new_position_value: float) -> float:
        """Calculate total exposure to a specific symbol"""
        current_exposure = 0
        for pos in positions:
            if pos.get("symbol") == symbol:
                current_exposure += pos.get("market_value", 0)
        
        return current_exposure + new_position_value
    
    def _assess_sector_concentration(
        self, positions: List[Dict], sector: str, new_position_value: float, portfolio_value: float
    ) -> float:
        """Assess sector concentration risk"""
        sector_exposure = new_position_value
        
        for pos in positions:
            if pos.get("sector") == sector:
                sector_exposure += pos.get("market_value", 0)
        
        sector_percentage = sector_exposure / portfolio_value
        
        if sector_percentage > self.max_sector_concentration:
            return 50
        elif sector_percentage > self.max_sector_concentration * 0.8:
            return 25
        else:
            return 0
    
    def _calculate_position_sizing(
        self, symbol: str, price: float, portfolio_value: float, market_data: Optional[Dict]
    ) -> PositionSizing:
        """Calculate optimal position sizing using various methods"""
        
        # Method 1: Fixed percentage
        fixed_percentage_value = portfolio_value * self.max_position_size
        fixed_percentage_qty = int(fixed_percentage_value / price)
        
        # Method 2: Risk-based sizing (Kelly Criterion approximation)
        risk_based_qty = fixed_percentage_qty
        if market_data:
            volatility = market_data.get("volatility", 0.2)
            expected_return = market_data.get("expected_return", 0.1)
            
            # Simplified Kelly Criterion
            if volatility > 0:
                kelly_fraction = max(0, min(0.25, expected_return / (volatility ** 2)))
                risk_based_value = portfolio_value * kelly_fraction
                risk_based_qty = int(risk_based_value / price)
        
        # Method 3: Volatility-adjusted sizing
        volatility_adjusted_qty = fixed_percentage_qty
        if market_data and market_data.get("volatility"):
            volatility = market_data["volatility"]
            # Reduce position size for high volatility stocks
            volatility_multiplier = max(0.2, 1 - (volatility - 0.2))
            volatility_adjusted_qty = int(fixed_percentage_qty * volatility_multiplier)
        
        # Take the most conservative approach
        recommended_qty = min(fixed_percentage_qty, risk_based_qty, volatility_adjusted_qty)
        max_qty = fixed_percentage_qty
        
        return PositionSizing(
            recommended_quantity=recommended_qty,
            max_quantity=max_qty,
            risk_amount=portfolio_value * self.max_portfolio_risk,
            position_value=recommended_qty * price,
            portfolio_percentage=(recommended_qty * price) / portfolio_value
        )
    
    def _calculate_risk_levels(
        self, price: float, side: str, market_data: Optional[Dict]
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit levels"""
        
        if not market_data:
            # Default risk levels
            if side == "buy":
                stop_loss = price * 0.95  # 5% stop loss
                take_profit = price * 1.15  # 15% take profit
            else:
                stop_loss = price * 1.05
                take_profit = price * 0.85
            
            return stop_loss, take_profit
        
        # Volatility-based risk levels
        volatility = market_data.get("volatility", 0.2)
        
        # Use 2 standard deviations for stop loss (approximately 95% confidence)
        daily_volatility = volatility / np.sqrt(252)  # Annualized to daily
        stop_distance = 2 * daily_volatility * price
        
        # Risk-reward ratio of 1:2
        profit_distance = 2 * stop_distance
        
        if side == "buy":
            stop_loss = price - stop_distance
            take_profit = price + profit_distance
        else:
            stop_loss = price + stop_distance
            take_profit = price - profit_distance
        
        return stop_loss, take_profit
    
    async def check_portfolio_risk(self, positions: List[Dict], portfolio_value: float) -> RiskMetrics:
        """Calculate overall portfolio risk metrics"""
        
        total_exposure = sum(pos.get("market_value", 0) for pos in positions)
        leverage_ratio = total_exposure / portfolio_value if portfolio_value > 0 else 0
        
        # Calculate sector concentration
        sector_exposure = {}
        for pos in positions:
            sector = pos.get("sector", "Unknown")
            sector_exposure[sector] = sector_exposure.get(sector, 0) + pos.get("market_value", 0)
        
        sector_concentration = {
            sector: exposure / portfolio_value 
            for sector, exposure in sector_exposure.items()
        }
        
        # Calculate concentration risk (Herfindahl index)
        position_weights = [pos.get("market_value", 0) / portfolio_value for pos in positions]
        concentration_risk = sum(weight ** 2 for weight in position_weights)
        
        # Placeholder for more complex calculations
        daily_var = portfolio_value * 0.02  # Simplified 2% VaR
        max_drawdown = 0.15  # Placeholder
        sharpe_ratio = 1.5  # Placeholder
        beta = 1.0  # Placeholder
        
        return RiskMetrics(
            portfolio_value=portfolio_value,
            total_exposure=total_exposure,
            leverage_ratio=leverage_ratio,
            concentration_risk=concentration_risk,
            sector_concentration=sector_concentration,
            daily_var=daily_var,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            beta=beta
        )
    
    async def validate_order(
        self, order_data: Dict, user_settings: Dict, portfolio_data: Dict
    ) -> Tuple[bool, List[str]]:
        """Validate an order against risk management rules"""
        
        errors = []
        
        # Check if trading is enabled
        if not user_settings.get("trading_enabled", False):
            errors.append("Trading is disabled for this account")
        
        # Check daily loss limits
        daily_pnl = portfolio_data.get("daily_pnl", 0)
        if daily_pnl < -abs(portfolio_data.get("portfolio_value", 0) * self.max_daily_loss):
            errors.append("Daily loss limit exceeded")
        
        # Check position size
        position_value = order_data["quantity"] * order_data["price"]
        portfolio_value = portfolio_data.get("portfolio_value", 0)
        
        if position_value > portfolio_value * self.max_position_size:
            errors.append(f"Position size exceeds maximum allowed ({self.max_position_size:.1%})")
        
        # Check available buying power
        buying_power = portfolio_data.get("buying_power", 0)
        if order_data["side"] == "buy" and position_value > buying_power:
            errors.append("Insufficient buying power")
        
        return len(errors) == 0, errors
    
    def update_risk_settings(self, settings: Dict):
        """Update risk management settings"""
        if "max_position_size" in settings:
            self.max_position_size = settings["max_position_size"]
        if "max_portfolio_risk" in settings:
            self.max_portfolio_risk = settings["max_portfolio_risk"]
        if "max_daily_loss" in settings:
            self.max_daily_loss = settings["max_daily_loss"]
        if "max_sector_concentration" in settings:
            self.max_sector_concentration = settings["max_sector_concentration"]
        
        logger.info("Risk management settings updated")

# Singleton instance
risk_manager = RiskManager()