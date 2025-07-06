"""
Advanced Options Trading Strategies
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
import math

from app.services.options_pricing import OptionsPricingService, OptionsGreeks


@dataclass
class StrategyLeg:
    """Individual leg of an options strategy"""
    option_type: str  # 'call', 'put', 'stock'
    side: str  # 'long', 'short'
    quantity: int
    strike_price: Optional[float] = None
    expiration_date: Optional[datetime] = None
    premium: Optional[float] = None
    symbol: Optional[str] = None


class AdvancedOptionsStrategies:
    """Collection of advanced options strategies"""
    
    def __init__(self, pricing_service: OptionsPricingService):
        self.pricing_service = pricing_service
    
    def create_long_straddle(self, underlying_symbol: str, strike_price: float,
                           expiration_date: datetime, call_premium: float,
                           put_premium: float) -> Dict[str, Any]:
        """Long Straddle: Buy call and put with same strike and expiration"""
        legs = [
            StrategyLeg('call', 'long', 1, strike_price, expiration_date, call_premium),
            StrategyLeg('put', 'long', 1, strike_price, expiration_date, put_premium)
        ]
        
        total_cost = call_premium + put_premium
        
        return {
            'strategy_type': 'long_straddle',
            'underlying_symbol': underlying_symbol,
            'name': f'Long Straddle {underlying_symbol} {strike_price}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'high_volatility',
            'description': f'Long straddle expecting significant price movement in {underlying_symbol}',
            'max_profit': None,  # Unlimited
            'max_loss': total_cost,
            'breakeven_points': [strike_price - total_cost, strike_price + total_cost],
            'cost_basis': total_cost
        }
    
    def create_short_straddle(self, underlying_symbol: str, strike_price: float,
                            expiration_date: datetime, call_premium: float,
                            put_premium: float) -> Dict[str, Any]:
        """Short Straddle: Sell call and put with same strike and expiration"""
        legs = [
            StrategyLeg('call', 'short', 1, strike_price, expiration_date, call_premium),
            StrategyLeg('put', 'short', 1, strike_price, expiration_date, put_premium)
        ]
        
        total_credit = call_premium + put_premium
        
        return {
            'strategy_type': 'short_straddle',
            'underlying_symbol': underlying_symbol,
            'name': f'Short Straddle {underlying_symbol} {strike_price}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'low_volatility',
            'description': f'Short straddle expecting low volatility in {underlying_symbol}',
            'max_profit': total_credit,
            'max_loss': None,  # Unlimited
            'breakeven_points': [strike_price - total_credit, strike_price + total_credit],
            'cost_basis': -total_credit
        }
    
    def create_long_strangle(self, underlying_symbol: str, put_strike: float,
                           call_strike: float, expiration_date: datetime,
                           call_premium: float, put_premium: float) -> Dict[str, Any]:
        """Long Strangle: Buy OTM call and OTM put"""
        if call_strike <= put_strike:
            raise ValueError("Call strike must be higher than put strike for strangle")
        
        legs = [
            StrategyLeg('put', 'long', 1, put_strike, expiration_date, put_premium),
            StrategyLeg('call', 'long', 1, call_strike, expiration_date, call_premium)
        ]
        
        total_cost = call_premium + put_premium
        
        return {
            'strategy_type': 'long_strangle',
            'underlying_symbol': underlying_symbol,
            'name': f'Long Strangle {underlying_symbol} {put_strike}/{call_strike}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'high_volatility',
            'description': f'Long strangle expecting large price movement in {underlying_symbol}',
            'max_profit': None,  # Unlimited
            'max_loss': total_cost,
            'breakeven_points': [put_strike - total_cost, call_strike + total_cost],
            'cost_basis': total_cost
        }
    
    def create_bull_call_spread(self, underlying_symbol: str, long_strike: float,
                              short_strike: float, expiration_date: datetime,
                              long_call_premium: float, short_call_premium: float) -> Dict[str, Any]:
        """Bull Call Spread: Buy lower strike call, sell higher strike call"""
        if short_strike <= long_strike:
            raise ValueError("Short strike must be higher than long strike for bull spread")
        
        legs = [
            StrategyLeg('call', 'long', 1, long_strike, expiration_date, long_call_premium),
            StrategyLeg('call', 'short', 1, short_strike, expiration_date, short_call_premium)
        ]
        
        net_cost = long_call_premium - short_call_premium
        max_profit = (short_strike - long_strike) - net_cost
        
        return {
            'strategy_type': 'bull_call_spread',
            'underlying_symbol': underlying_symbol,
            'name': f'Bull Call Spread {underlying_symbol} {long_strike}/{short_strike}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'moderately_bullish',
            'description': f'Bull call spread on {underlying_symbol}',
            'max_profit': max_profit,
            'max_loss': net_cost,
            'breakeven_points': [long_strike + net_cost],
            'cost_basis': net_cost
        }
    
    def create_bear_put_spread(self, underlying_symbol: str, long_strike: float,
                             short_strike: float, expiration_date: datetime,
                             long_put_premium: float, short_put_premium: float) -> Dict[str, Any]:
        """Bear Put Spread: Buy higher strike put, sell lower strike put"""
        if long_strike <= short_strike:
            raise ValueError("Long strike must be higher than short strike for bear put spread")
        
        legs = [
            StrategyLeg('put', 'long', 1, long_strike, expiration_date, long_put_premium),
            StrategyLeg('put', 'short', 1, short_strike, expiration_date, short_put_premium)
        ]
        
        net_cost = long_put_premium - short_put_premium
        max_profit = (long_strike - short_strike) - net_cost
        
        return {
            'strategy_type': 'bear_put_spread',
            'underlying_symbol': underlying_symbol,
            'name': f'Bear Put Spread {underlying_symbol} {short_strike}/{long_strike}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'moderately_bearish',
            'description': f'Bear put spread on {underlying_symbol}',
            'max_profit': max_profit,
            'max_loss': net_cost,
            'breakeven_points': [long_strike - net_cost],
            'cost_basis': net_cost
        }
    
    def create_iron_butterfly(self, underlying_symbol: str, center_strike: float,
                            wing_strikes: Tuple[float, float], expiration_date: datetime,
                            premiums: Dict[str, float]) -> Dict[str, Any]:
        """Iron Butterfly: Short straddle with protective wings"""
        lower_wing, upper_wing = wing_strikes
        
        if not (lower_wing < center_strike < upper_wing):
            raise ValueError("Center strike must be between wing strikes")
        
        legs = [
            StrategyLeg('put', 'long', 1, lower_wing, expiration_date, premiums['long_put']),
            StrategyLeg('put', 'short', 1, center_strike, expiration_date, premiums['short_put']),
            StrategyLeg('call', 'short', 1, center_strike, expiration_date, premiums['short_call']),
            StrategyLeg('call', 'long', 1, upper_wing, expiration_date, premiums['long_call'])
        ]
        
        net_credit = (premiums['short_put'] + premiums['short_call'] - 
                     premiums['long_put'] - premiums['long_call'])
        max_loss = min(center_strike - lower_wing, upper_wing - center_strike) - net_credit
        
        return {
            'strategy_type': 'iron_butterfly',
            'underlying_symbol': underlying_symbol,
            'name': f'Iron Butterfly {underlying_symbol} {lower_wing}/{center_strike}/{upper_wing}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'neutral',
            'description': f'Iron butterfly centered at {center_strike}',
            'max_profit': net_credit,
            'max_loss': max_loss,
            'breakeven_points': [center_strike - net_credit, center_strike + net_credit],
            'cost_basis': -net_credit
        }
    
    def create_calendar_spread(self, underlying_symbol: str, strike_price: float,
                             near_expiration: datetime, far_expiration: datetime,
                             option_type: str, near_premium: float,
                             far_premium: float) -> Dict[str, Any]:
        """Calendar Spread: Sell near-term option, buy far-term option (same strike)"""
        if near_expiration >= far_expiration:
            raise ValueError("Near expiration must be before far expiration")
        
        legs = [
            StrategyLeg(option_type, 'short', 1, strike_price, near_expiration, near_premium),
            StrategyLeg(option_type, 'long', 1, strike_price, far_expiration, far_premium)
        ]
        
        net_cost = far_premium - near_premium
        
        return {
            'strategy_type': 'calendar_spread',
            'underlying_symbol': underlying_symbol,
            'name': f'Calendar Spread {underlying_symbol} {strike_price} {option_type}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'neutral',
            'description': f'Calendar spread on {underlying_symbol} {option_type}s',
            'max_profit': None,  # Depends on time decay and volatility
            'max_loss': net_cost,
            'breakeven_points': None,  # Complex to calculate
            'cost_basis': net_cost
        }
    
    def create_diagonal_spread(self, underlying_symbol: str, long_strike: float,
                             short_strike: float, near_expiration: datetime,
                             far_expiration: datetime, option_type: str,
                             long_premium: float, short_premium: float) -> Dict[str, Any]:
        """Diagonal Spread: Different strikes and expirations"""
        if near_expiration >= far_expiration:
            raise ValueError("Near expiration must be before far expiration")
        
        legs = [
            StrategyLeg(option_type, 'long', 1, long_strike, far_expiration, long_premium),
            StrategyLeg(option_type, 'short', 1, short_strike, near_expiration, short_premium)
        ]
        
        net_cost = long_premium - short_premium
        
        return {
            'strategy_type': 'diagonal_spread',
            'underlying_symbol': underlying_symbol,
            'name': f'Diagonal Spread {underlying_symbol} {long_strike}/{short_strike}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'neutral_directional',
            'description': f'Diagonal spread with different strikes and expirations',
            'max_profit': None,  # Variable based on price movement and time
            'max_loss': net_cost,
            'breakeven_points': None,  # Complex calculation
            'cost_basis': net_cost
        }
    
    def create_collar(self, underlying_symbol: str, stock_quantity: int,
                    put_strike: float, call_strike: float, expiration_date: datetime,
                    put_premium: float, call_premium: float) -> Dict[str, Any]:
        """Collar: Own stock + protective put + covered call"""
        legs = [
            StrategyLeg('stock', 'long', stock_quantity, symbol=underlying_symbol),
            StrategyLeg('put', 'long', stock_quantity // 100, put_strike, expiration_date, put_premium),
            StrategyLeg('call', 'short', stock_quantity // 100, call_strike, expiration_date, call_premium)
        ]
        
        net_cost = put_premium - call_premium
        
        return {
            'strategy_type': 'collar',
            'underlying_symbol': underlying_symbol,
            'name': f'Collar {underlying_symbol} {put_strike}/{call_strike}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'neutral_protective',
            'description': f'Protective collar on {stock_quantity} shares',
            'max_profit': None,  # Limited by call strike
            'max_loss': None,  # Limited by put strike
            'breakeven_points': None,  # Depends on stock entry price
            'cost_basis': net_cost
        }
    
    def create_jade_lizard(self, underlying_symbol: str, put_strike: float,
                         call_strike_short: float, call_strike_long: float,
                         expiration_date: datetime, premiums: Dict[str, float]) -> Dict[str, Any]:
        """Jade Lizard: Short put + short call spread"""
        legs = [
            StrategyLeg('put', 'short', 1, put_strike, expiration_date, premiums['short_put']),
            StrategyLeg('call', 'short', 1, call_strike_short, expiration_date, premiums['short_call']),
            StrategyLeg('call', 'long', 1, call_strike_long, expiration_date, premiums['long_call'])
        ]
        
        net_credit = (premiums['short_put'] + premiums['short_call'] - premiums['long_call'])
        
        return {
            'strategy_type': 'jade_lizard',
            'underlying_symbol': underlying_symbol,
            'name': f'Jade Lizard {underlying_symbol}',
            'legs': [leg.__dict__ for leg in legs],
            'market_outlook': 'neutral_bullish',
            'description': f'Jade lizard strategy on {underlying_symbol}',
            'max_profit': net_credit,
            'max_loss': None,  # Can be significant on downside
            'breakeven_points': [put_strike - net_credit],
            'cost_basis': -net_credit
        }


class StrategyScreener:
    """Screen for optimal options strategies based on market conditions"""
    
    def __init__(self, pricing_service: OptionsPricingService):
        self.pricing_service = pricing_service
    
    def screen_covered_calls(self, underlying_price: float, positions: List[Dict],
                           options_chain: List[Dict], target_return: float = 0.02) -> List[Dict]:
        """Screen for optimal covered call opportunities"""
        opportunities = []
        
        for position in positions:
            if position['quantity'] >= 100:  # Must own at least 100 shares
                stock_symbol = position['symbol']
                
                # Find suitable call options
                calls = [opt for opt in options_chain 
                        if opt['underlying_symbol'] == stock_symbol 
                        and opt['option_type'] == 'call'
                        and opt['strike_price'] > underlying_price]
                
                for call in calls:
                    # Calculate potential return
                    premium_income = call['bid'] * 100  # Per contract
                    strike_diff = max(0, call['strike_price'] - underlying_price)
                    total_return = (premium_income + strike_diff) / (underlying_price * 100)
                    
                    if total_return >= target_return:
                        opportunities.append({
                            'strategy': 'covered_call',
                            'underlying_symbol': stock_symbol,
                            'call_strike': call['strike_price'],
                            'expiration': call['expiration_date'],
                            'premium': call['bid'],
                            'potential_return': total_return,
                            'delta': call.get('delta', 0),
                            'probability_profit': abs(call.get('delta', 0))  # Approximation
                        })
        
        return sorted(opportunities, key=lambda x: x['potential_return'], reverse=True)
    
    def screen_cash_secured_puts(self, available_cash: float, options_chain: List[Dict],
                               target_return: float = 0.01) -> List[Dict]:
        """Screen for cash-secured put opportunities"""
        opportunities = []
        
        puts = [opt for opt in options_chain if opt['option_type'] == 'put']
        
        for put in puts:
            strike_price = put['strike_price']
            required_cash = strike_price * 100  # Cash to secure the put
            
            if required_cash <= available_cash:
                premium_income = put['bid'] * 100
                potential_return = premium_income / required_cash
                
                if potential_return >= target_return:
                    opportunities.append({
                        'strategy': 'cash_secured_put',
                        'underlying_symbol': put['underlying_symbol'],
                        'put_strike': strike_price,
                        'expiration': put['expiration_date'],
                        'premium': put['bid'],
                        'required_cash': required_cash,
                        'potential_return': potential_return,
                        'delta': put.get('delta', 0),
                        'probability_profit': 1 - abs(put.get('delta', 0))  # Approximation
                    })
        
        return sorted(opportunities, key=lambda x: x['potential_return'], reverse=True)
    
    def screen_iron_condors(self, options_chain: List[Dict], underlying_price: float,
                          min_credit: float = 0.5) -> List[Dict]:
        """Screen for iron condor opportunities"""
        opportunities = []
        
        # Group options by expiration
        expirations = {}
        for opt in options_chain:
            exp_date = opt['expiration_date']
            if exp_date not in expirations:
                expirations[exp_date] = {'calls': [], 'puts': []}
            
            if opt['option_type'] == 'call':
                expirations[exp_date]['calls'].append(opt)
            else:
                expirations[exp_date]['puts'].append(opt)
        
        for exp_date, options in expirations.items():
            calls = sorted(options['calls'], key=lambda x: x['strike_price'])
            puts = sorted(options['puts'], key=lambda x: x['strike_price'])
            
            # Find OTM puts and calls
            otm_puts = [p for p in puts if p['strike_price'] < underlying_price]
            otm_calls = [c for c in calls if c['strike_price'] > underlying_price]
            
            if len(otm_puts) >= 2 and len(otm_calls) >= 2:
                # Try different strike combinations
                for i in range(len(otm_puts) - 1):
                    for j in range(len(otm_calls) - 1):
                        long_put = otm_puts[i]
                        short_put = otm_puts[i + 1]
                        short_call = otm_calls[j]
                        long_call = otm_calls[j + 1]
                        
                        # Calculate net credit
                        net_credit = (short_put['bid'] + short_call['bid'] - 
                                    long_put['ask'] - long_call['ask'])
                        
                        if net_credit >= min_credit:
                            # Calculate max loss
                            put_spread_width = short_put['strike_price'] - long_put['strike_price']
                            call_spread_width = long_call['strike_price'] - short_call['strike_price']
                            max_loss = min(put_spread_width, call_spread_width) - net_credit
                            
                            opportunities.append({
                                'strategy': 'iron_condor',
                                'underlying_symbol': long_put['underlying_symbol'],
                                'expiration': exp_date,
                                'strikes': {
                                    'long_put': long_put['strike_price'],
                                    'short_put': short_put['strike_price'],
                                    'short_call': short_call['strike_price'],
                                    'long_call': long_call['strike_price']
                                },
                                'net_credit': net_credit,
                                'max_loss': max_loss,
                                'return_on_risk': net_credit / max_loss if max_loss > 0 else 0,
                                'probability_profit': 0.7  # Rough estimate
                            })
        
        return sorted(opportunities, key=lambda x: x['return_on_risk'], reverse=True)


class StrategyOptimizer:
    """Optimize strategy parameters for maximum risk-adjusted returns"""
    
    def __init__(self, pricing_service: OptionsPricingService):
        self.pricing_service = pricing_service
    
    def optimize_covered_call_strike(self, stock_price: float, stock_quantity: int,
                                   available_calls: List[Dict], 
                                   target_probability: float = 0.7) -> Optional[Dict]:
        """Find optimal strike for covered call based on probability target"""
        best_strike = None
        best_score = 0
        
        for call in available_calls:
            delta = abs(call.get('delta', 0))
            probability_otm = 1 - delta  # Approximation
            
            if probability_otm >= target_probability:
                premium_yield = (call['bid'] * 100) / (stock_price * 100)
                
                # Score combines yield and probability
                score = premium_yield * probability_otm
                
                if score > best_score:
                    best_score = score
                    best_strike = {
                        'strike_price': call['strike_price'],
                        'premium': call['bid'],
                        'delta': delta,
                        'probability_otm': probability_otm,
                        'premium_yield': premium_yield,
                        'score': score
                    }
        
        return best_strike
    
    def optimize_iron_condor_width(self, underlying_price: float, 
                                 available_options: List[Dict],
                                 target_return_on_risk: float = 0.3) -> List[Dict]:
        """Find optimal strike width for iron condor"""
        optimal_strategies = []
        
        # Try different wing widths
        for width in [5, 10, 15, 20, 25, 30]:
            # Find strikes around current price
            center_puts = [opt for opt in available_options 
                          if opt['option_type'] == 'put' 
                          and abs(opt['strike_price'] - underlying_price) <= width/2]
            
            center_calls = [opt for opt in available_options 
                           if opt['option_type'] == 'call' 
                           and abs(opt['strike_price'] - underlying_price) <= width/2]
            
            for put in center_puts:
                for call in center_calls:
                    put_strike = put['strike_price']
                    call_strike = call['strike_price']
                    
                    # Find wing strikes
                    long_put_strike = put_strike - width
                    long_call_strike = call_strike + width
                    
                    # Find corresponding options
                    long_put = next((opt for opt in available_options 
                                   if opt['option_type'] == 'put' 
                                   and opt['strike_price'] == long_put_strike), None)
                    
                    long_call = next((opt for opt in available_options 
                                    if opt['option_type'] == 'call' 
                                    and opt['strike_price'] == long_call_strike), None)
                    
                    if long_put and long_call:
                        # Calculate strategy metrics
                        net_credit = (put['bid'] + call['bid'] - 
                                    long_put['ask'] - long_call['ask'])
                        max_loss = width - net_credit
                        
                        if max_loss > 0:
                            return_on_risk = net_credit / max_loss
                            
                            if return_on_risk >= target_return_on_risk:
                                optimal_strategies.append({
                                    'width': width,
                                    'net_credit': net_credit,
                                    'max_loss': max_loss,
                                    'return_on_risk': return_on_risk,
                                    'strikes': {
                                        'long_put': long_put_strike,
                                        'short_put': put_strike,
                                        'short_call': call_strike,
                                        'long_call': long_call_strike
                                    }
                                })
        
        return sorted(optimal_strategies, key=lambda x: x['return_on_risk'], reverse=True)