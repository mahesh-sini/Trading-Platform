"""
Options Pricing and Greeks Calculation Service
"""

import math
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from scipy.stats import norm
from dataclasses import dataclass

from app.models.options import OptionsContract, OptionType


@dataclass
class OptionsGreeks:
    """Greeks calculation results"""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    
    
@dataclass
class OptionsPriceData:
    """Options pricing calculation results"""
    theoretical_price: float
    intrinsic_value: float
    time_value: float
    greeks: OptionsGreeks
    implied_volatility: Optional[float] = None


class BlackScholesCalculator:
    """Black-Scholes options pricing model"""
    
    @staticmethod
    def calculate_d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> Tuple[float, float]:
        """Calculate d1 and d2 parameters for Black-Scholes"""
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        return d1, d2
    
    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate call option price using Black-Scholes"""
        if T <= 0:
            return max(S - K, 0)
        
        d1, d2 = BlackScholesCalculator.calculate_d1_d2(S, K, T, r, sigma)
        
        call_price = (S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2))
        return max(call_price, 0)
    
    @staticmethod
    def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate put option price using Black-Scholes"""
        if T <= 0:
            return max(K - S, 0)
        
        d1, d2 = BlackScholesCalculator.calculate_d1_d2(S, K, T, r, sigma)
        
        put_price = (K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))
        return max(put_price, 0)
    
    @staticmethod
    def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float, 
                        option_type: str) -> OptionsGreeks:
        """Calculate all Greeks for an option"""
        if T <= 0:
            # Handle expired options
            if option_type.lower() == 'call':
                delta = 1.0 if S > K else 0.0
            else:
                delta = -1.0 if S < K else 0.0
            
            return OptionsGreeks(
                delta=delta,
                gamma=0.0,
                theta=0.0,
                vega=0.0,
                rho=0.0
            )
        
        d1, d2 = BlackScholesCalculator.calculate_d1_d2(S, K, T, r, sigma)
        
        # Delta
        if option_type.lower() == 'call':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1
        
        # Gamma (same for calls and puts)
        gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
        
        # Theta
        theta_common = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
        if option_type.lower() == 'call':
            theta = (theta_common - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            theta = (theta_common + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
        
        # Vega (same for calls and puts)
        vega = S * norm.pdf(d1) * math.sqrt(T) / 100  # Per 1% volatility change
        
        # Rho
        if option_type.lower() == 'call':
            rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100  # Per 1% interest rate change
        else:
            rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100
        
        return OptionsGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho
        )


class ImpliedVolatilityCalculator:
    """Calculate implied volatility using Newton-Raphson method"""
    
    @staticmethod
    def calculate_implied_volatility(market_price: float, S: float, K: float, T: float, 
                                   r: float, option_type: str, 
                                   max_iterations: int = 100, tolerance: float = 1e-6) -> Optional[float]:
        """Calculate implied volatility using Newton-Raphson method"""
        if T <= 0:
            return None
            
        # Initial guess
        sigma = 0.3
        
        for i in range(max_iterations):
            # Calculate price and vega with current sigma
            if option_type.lower() == 'call':
                price = BlackScholesCalculator.call_price(S, K, T, r, sigma)
            else:
                price = BlackScholesCalculator.put_price(S, K, T, r, sigma)
            
            # Calculate vega
            d1, _ = BlackScholesCalculator.calculate_d1_d2(S, K, T, r, sigma)
            vega = S * norm.pdf(d1) * math.sqrt(T)
            
            # Check for convergence
            price_diff = price - market_price
            if abs(price_diff) < tolerance:
                return sigma
            
            # Newton-Raphson update
            if vega == 0:
                break
                
            sigma_new = sigma - price_diff / vega
            
            # Ensure sigma stays positive
            if sigma_new <= 0:
                sigma = sigma / 2
            else:
                sigma = sigma_new
        
        return sigma if sigma > 0 else None


class OptionsPricingService:
    """Service for options pricing calculations"""
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
        self.bs_calculator = BlackScholesCalculator()
        self.iv_calculator = ImpliedVolatilityCalculator()
    
    def calculate_time_to_expiration(self, expiration_date: datetime) -> float:
        """Calculate time to expiration in years"""
        now = datetime.now(expiration_date.tzinfo) if expiration_date.tzinfo else datetime.now()
        time_diff = expiration_date - now
        
        # Convert to years (using 365.25 days per year)
        years = time_diff.total_seconds() / (365.25 * 24 * 3600)
        return max(years, 0)
    
    def calculate_intrinsic_value(self, underlying_price: float, strike_price: float, 
                                option_type: str) -> float:
        """Calculate intrinsic value of an option"""
        if option_type.lower() == 'call':
            return max(underlying_price - strike_price, 0)
        else:
            return max(strike_price - underlying_price, 0)
    
    def price_option(self, underlying_price: float, strike_price: float, 
                    expiration_date: datetime, option_type: str, 
                    volatility: float, dividend_yield: float = 0.0) -> OptionsPriceData:
        """Calculate option price and Greeks"""
        
        time_to_expiration = self.calculate_time_to_expiration(expiration_date)
        
        # Adjust for dividend yield
        adjusted_spot = underlying_price * math.exp(-dividend_yield * time_to_expiration)
        
        # Calculate theoretical price
        if option_type.lower() == 'call':
            theoretical_price = self.bs_calculator.call_price(
                adjusted_spot, strike_price, time_to_expiration, 
                self.risk_free_rate, volatility
            )
        else:
            theoretical_price = self.bs_calculator.put_price(
                adjusted_spot, strike_price, time_to_expiration, 
                self.risk_free_rate, volatility
            )
        
        # Calculate intrinsic and time value
        intrinsic_value = self.calculate_intrinsic_value(
            underlying_price, strike_price, option_type
        )
        time_value = max(theoretical_price - intrinsic_value, 0)
        
        # Calculate Greeks
        greeks = self.bs_calculator.calculate_greeks(
            adjusted_spot, strike_price, time_to_expiration, 
            self.risk_free_rate, volatility, option_type
        )
        
        return OptionsPriceData(
            theoretical_price=theoretical_price,
            intrinsic_value=intrinsic_value,
            time_value=time_value,
            greeks=greeks
        )
    
    def calculate_implied_volatility(self, market_price: float, underlying_price: float, 
                                   strike_price: float, expiration_date: datetime, 
                                   option_type: str, dividend_yield: float = 0.0) -> Optional[float]:
        """Calculate implied volatility from market price"""
        
        time_to_expiration = self.calculate_time_to_expiration(expiration_date)
        
        if time_to_expiration <= 0:
            return None
        
        # Adjust for dividend yield
        adjusted_spot = underlying_price * math.exp(-dividend_yield * time_to_expiration)
        
        return self.iv_calculator.calculate_implied_volatility(
            market_price, adjusted_spot, strike_price, time_to_expiration,
            self.risk_free_rate, option_type
        )
    
    def black_scholes_price(self, S: float, K: float, T: float, r: float, sigma: float, 
                           option_type: str) -> float:
        """Calculate Black-Scholes option price - compatibility method"""
        if option_type.lower() == 'call':
            return self.bs_calculator.call_price(S, K, T, r, sigma)
        else:
            return self.bs_calculator.put_price(S, K, T, r, sigma)
    
    def update_contract_pricing(self, contract: OptionsContract, 
                              underlying_price: float, volatility: float = None) -> OptionsContract:
        """Update options contract with latest pricing data"""
        
        time_to_expiration = self.calculate_time_to_expiration(contract.expiration_date)
        contract.time_to_expiration = Decimal(str(time_to_expiration))
        
        # Use implied volatility if available, otherwise use provided volatility
        if contract.last_price and contract.last_price > 0:
            iv = self.calculate_implied_volatility(
                float(contract.last_price), underlying_price, 
                float(contract.strike_price), contract.expiration_date,
                contract.option_type.value
            )
            if iv:
                contract.implied_volatility = Decimal(str(iv))
                volatility = iv
        
        if volatility:
            # Calculate pricing data
            pricing_data = self.price_option(
                underlying_price, float(contract.strike_price),
                contract.expiration_date, contract.option_type.value, volatility
            )
            
            # Update contract fields
            contract.theoretical_price = Decimal(str(pricing_data.theoretical_price))
            contract.intrinsic_value = Decimal(str(pricing_data.intrinsic_value))
            contract.time_value = Decimal(str(pricing_data.time_value))
            
            # Update Greeks
            contract.delta = Decimal(str(pricing_data.greeks.delta))
            contract.gamma = Decimal(str(pricing_data.greeks.gamma))
            contract.theta = Decimal(str(pricing_data.greeks.theta))
            contract.vega = Decimal(str(pricing_data.greeks.vega))
            contract.rho = Decimal(str(pricing_data.greeks.rho))
        
        return contract


class VolatilityCalculator:
    """Calculate historical and realized volatility"""
    
    @staticmethod
    def calculate_historical_volatility(prices: List[float], 
                                      periods: int = 252) -> float:
        """Calculate historical volatility from price series"""
        if len(prices) < 2:
            return 0.0
        
        # Calculate log returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append(math.log(prices[i] / prices[i-1]))
        
        if not returns:
            return 0.0
        
        # Calculate standard deviation and annualize
        std_dev = np.std(returns, ddof=1)
        annualized_vol = std_dev * math.sqrt(periods)
        
        return annualized_vol
    
    @staticmethod
    def calculate_garch_volatility(returns: List[float], 
                                 alpha: float = 0.1, beta: float = 0.8) -> float:
        """Calculate GARCH(1,1) volatility forecast"""
        if len(returns) < 2:
            return 0.0
        
        # Initialize with historical variance
        long_run_var = np.var(returns, ddof=1)
        omega = long_run_var * (1 - alpha - beta)
        
        # Current variance estimate
        var_t = long_run_var
        
        # Update with latest return
        if returns:
            var_t = omega + alpha * (returns[-1]**2) + beta * var_t
        
        return math.sqrt(var_t * 252)  # Annualized volatility


class OptionsStrategyCalculator:
    """Calculate P&L and risk metrics for options strategies"""
    
    def __init__(self, pricing_service: OptionsPricingService):
        self.pricing_service = pricing_service
    
    def calculate_strategy_greeks(self, legs: List[Dict]) -> OptionsGreeks:
        """Calculate net Greeks for a multi-leg strategy"""
        net_delta = 0.0
        net_gamma = 0.0
        net_theta = 0.0
        net_vega = 0.0
        net_rho = 0.0
        
        for leg in legs:
            quantity = leg.get('quantity', 0)
            greeks = leg.get('greeks', {})
            
            net_delta += quantity * greeks.get('delta', 0)
            net_gamma += quantity * greeks.get('gamma', 0)
            net_theta += quantity * greeks.get('theta', 0)
            net_vega += quantity * greeks.get('vega', 0)
            net_rho += quantity * greeks.get('rho', 0)
        
        return OptionsGreeks(
            delta=net_delta,
            gamma=net_gamma,
            theta=net_theta,
            vega=net_vega,
            rho=net_rho
        )
    
    def calculate_payoff_diagram(self, legs: List[Dict], 
                               underlying_range: Tuple[float, float],
                               num_points: int = 100) -> List[Dict]:
        """Calculate payoff diagram for options strategy"""
        min_price, max_price = underlying_range
        price_step = (max_price - min_price) / num_points
        
        payoff_points = []
        
        for i in range(num_points + 1):
            underlying_price = min_price + i * price_step
            total_payoff = 0.0
            
            for leg in legs:
                option_type = leg.get('option_type')
                strike_price = leg.get('strike_price')
                quantity = leg.get('quantity', 0)
                premium_paid = leg.get('premium_paid', 0)
                
                # Calculate payoff for this leg
                if option_type.lower() == 'call':
                    intrinsic = max(underlying_price - strike_price, 0)
                else:
                    intrinsic = max(strike_price - underlying_price, 0)
                
                leg_payoff = quantity * (intrinsic - premium_paid)
                total_payoff += leg_payoff
            
            payoff_points.append({
                'underlying_price': underlying_price,
                'payoff': total_payoff
            })
        
        return payoff_points
    
    def find_breakeven_points(self, payoff_diagram: List[Dict]) -> List[float]:
        """Find breakeven points from payoff diagram"""
        breakeven_points = []
        
        for i in range(len(payoff_diagram) - 1):
            current_payoff = payoff_diagram[i]['payoff']
            next_payoff = payoff_diagram[i + 1]['payoff']
            
            # Check if payoff crosses zero
            if (current_payoff <= 0 <= next_payoff) or (current_payoff >= 0 >= next_payoff):
                # Linear interpolation to find exact breakeven point
                current_price = payoff_diagram[i]['underlying_price']
                next_price = payoff_diagram[i + 1]['underlying_price']
                
                if next_payoff != current_payoff:
                    breakeven_price = current_price - current_payoff * (next_price - current_price) / (next_payoff - current_payoff)
                    breakeven_points.append(breakeven_price)
        
        return breakeven_points
    
    def calculate_max_profit_loss(self, payoff_diagram: List[Dict]) -> Tuple[Optional[float], Optional[float]]:
        """Calculate maximum profit and loss from payoff diagram"""
        payoffs = [point['payoff'] for point in payoff_diagram]
        
        max_profit = max(payoffs) if payoffs else None
        max_loss = min(payoffs) if payoffs else None
        
        # Check if profit is unlimited (increasing at edges)
        if len(payoffs) >= 2:
            if payoffs[-1] > payoffs[-2] and payoffs[-1] - payoffs[-2] > 0.01:
                max_profit = None  # Unlimited profit
        
        return max_profit, max_loss