import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from services.strategy_engine import BaseStrategy, TradingSignal, SignalType
from services.data_service import data_service

logger = logging.getLogger(__name__)

@dataclass
class BacktestTrade:
    """Represents a trade in backtesting"""
    timestamp: datetime
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: int
    price: float
    commission: float = 0.0
    strategy_id: str = ""
    signal_reason: str = ""

@dataclass
class BacktestPosition:
    """Represents a position during backtesting"""
    symbol: str
    quantity: int = 0
    average_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_value: float = 0.0

@dataclass
class BacktestPortfolio:
    """Portfolio state during backtesting"""
    cash: float
    positions: Dict[str, BacktestPosition] = field(default_factory=dict)
    total_value: float = 0.0
    daily_returns: List[float] = field(default_factory=list)
    trades: List[BacktestTrade] = field(default_factory=list)
    
    def add_position(self, symbol: str):
        if symbol not in self.positions:
            self.positions[symbol] = BacktestPosition(symbol=symbol)

@dataclass
class BacktestMetrics:
    """Performance metrics from backtesting"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_trade_duration: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0

class BacktestingEngine:
    """Comprehensive backtesting engine for trading strategies"""
    
    def __init__(self, initial_capital: float = 100000.0, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.portfolio = None
        self.market_data = {}
        self.current_date = None
        
    async def run_backtest(
        self,
        strategy: BaseStrategy,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        data_frequency: str = "1d"
    ) -> Dict[str, Any]:
        """Run comprehensive backtest for a strategy"""
        
        logger.info(f"Starting backtest for strategy {strategy.strategy_id}")
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Symbols: {symbols}")
        
        # Initialize portfolio
        self.portfolio = BacktestPortfolio(cash=self.initial_capital)
        for symbol in symbols:
            self.portfolio.add_position(symbol)
        
        # Load historical data
        historical_data = await self._load_historical_data(symbols, start_date, end_date, data_frequency)
        
        if not historical_data:
            raise ValueError("No historical data available for backtesting")
        
        # Get all trading dates
        all_dates = sorted(set().union(*[df.index for df in historical_data.values()]))
        
        # Run simulation
        for current_date in all_dates:
            self.current_date = current_date
            
            # Update portfolio value
            await self._update_portfolio_value(current_date, historical_data)
            
            # Generate market data snapshot for this date
            market_snapshot = self._create_market_snapshot(current_date, historical_data)
            
            # Process each symbol
            for symbol in symbols:
                if symbol in market_snapshot:
                    # Generate signal
                    signal = await strategy.generate_signal(market_snapshot[symbol])
                    
                    if signal:
                        # Calculate position size
                        signal.quantity = strategy.calculate_position_size(signal, self.portfolio.total_value)
                        
                        # Execute signal
                        await self._execute_backtest_signal(signal)
        
        # Calculate final metrics
        metrics = self._calculate_performance_metrics()
        
        # Prepare results
        results = {
            "strategy_id": strategy.strategy_id,
            "backtest_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "duration_days": (end_date - start_date).days
            },
            "initial_capital": self.initial_capital,
            "final_value": self.portfolio.total_value,
            "metrics": metrics.__dict__,
            "trades": [self._trade_to_dict(trade) for trade in self.portfolio.trades],
            "daily_returns": self.portfolio.daily_returns,
            "positions": {symbol: pos.__dict__ for symbol, pos in self.portfolio.positions.items()}
        }
        
        logger.info(f"Backtest completed. Final value: ${self.portfolio.total_value:,.2f}")
        logger.info(f"Total return: {metrics.total_return:.2%}")
        logger.info(f"Total trades: {metrics.total_trades}")
        
        return results
    
    async def _load_historical_data(
        self, 
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime,
        frequency: str
    ) -> Dict[str, pd.DataFrame]:
        """Load historical market data for backtesting"""
        
        historical_data = {}
        
        for symbol in symbols:
            try:
                # This would integrate with the data service
                # For now, generate mock data
                data = await self._generate_mock_data(symbol, start_date, end_date, frequency)
                historical_data[symbol] = data
                
                logger.info(f"Loaded {len(data)} data points for {symbol}")
                
            except Exception as e:
                logger.error(f"Failed to load data for {symbol}: {str(e)}")
        
        return historical_data
    
    async def _generate_mock_data(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime, 
        frequency: str
    ) -> pd.DataFrame:
        """Generate mock historical data for backtesting"""
        
        # Create date range
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        
        # Generate realistic price data using random walk
        np.random.seed(42)  # For reproducible results
        initial_price = 100.0
        volatility = 0.02
        drift = 0.0005
        
        returns = np.random.normal(drift, volatility, len(dates))
        prices = [initial_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data
        data = pd.DataFrame(index=dates)
        data['close'] = prices
        data['open'] = data['close'].shift(1).fillna(initial_price)
        data['high'] = data[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, 0.02, len(data)))
        data['low'] = data[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, 0.02, len(data)))
        data['volume'] = np.random.randint(100000, 1000000, len(data))
        
        return data
    
    def _create_market_snapshot(self, current_date: datetime, historical_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
        """Create market data snapshot for a specific date"""
        
        snapshot = {}
        
        for symbol, df in historical_data.items():
            if current_date in df.index:
                # Get historical prices up to current date
                historical_prices = df.loc[:current_date]['close'].tolist()
                
                snapshot[symbol] = {
                    "symbol": symbol,
                    "current_price": df.loc[current_date]['close'],
                    "prices": historical_prices,
                    "volume": df.loc[current_date]['volume'],
                    "high": df.loc[current_date]['high'],
                    "low": df.loc[current_date]['low'],
                    "open": df.loc[current_date]['open']
                }
        
        return snapshot
    
    async def _execute_backtest_signal(self, signal: TradingSignal):
        """Execute a trading signal in the backtest"""
        
        try:
            commission = signal.quantity * signal.price * self.commission_rate
            
            if signal.signal == SignalType.BUY:
                total_cost = signal.quantity * signal.price + commission
                
                if self.portfolio.cash >= total_cost:
                    # Execute buy
                    self.portfolio.cash -= total_cost
                    
                    position = self.portfolio.positions[signal.symbol]
                    old_quantity = position.quantity
                    old_avg_price = position.average_price
                    
                    new_quantity = old_quantity + signal.quantity
                    if new_quantity > 0:
                        position.average_price = (
                            (old_quantity * old_avg_price + signal.quantity * signal.price) / new_quantity
                        )
                    position.quantity = new_quantity
                    
                    # Record trade
                    trade = BacktestTrade(
                        timestamp=self.current_date,
                        symbol=signal.symbol,
                        action="buy",
                        quantity=signal.quantity,
                        price=signal.price,
                        commission=commission,
                        strategy_id=signal.reason,
                        signal_reason=signal.reason
                    )
                    self.portfolio.trades.append(trade)
                    
                    logger.debug(f"BUY executed: {signal.symbol} {signal.quantity}@{signal.price}")
                
            elif signal.signal == SignalType.SELL:
                position = self.portfolio.positions[signal.symbol]
                
                if position.quantity >= signal.quantity:
                    # Execute sell
                    total_proceeds = signal.quantity * signal.price - commission
                    self.portfolio.cash += total_proceeds
                    
                    # Calculate realized PnL
                    realized_pnl = signal.quantity * (signal.price - position.average_price)
                    position.realized_pnl += realized_pnl
                    position.quantity -= signal.quantity
                    
                    # Record trade
                    trade = BacktestTrade(
                        timestamp=self.current_date,
                        symbol=signal.symbol,
                        action="sell",
                        quantity=signal.quantity,
                        price=signal.price,
                        commission=commission,
                        strategy_id=signal.reason,
                        signal_reason=signal.reason
                    )
                    self.portfolio.trades.append(trade)
                    
                    logger.debug(f"SELL executed: {signal.symbol} {signal.quantity}@{signal.price}")
                    
        except Exception as e:
            logger.error(f"Error executing backtest signal: {str(e)}")
    
    async def _update_portfolio_value(self, current_date: datetime, historical_data: Dict[str, pd.DataFrame]):
        """Update portfolio value for current date"""
        
        equity_value = 0.0
        
        for symbol, position in self.portfolio.positions.items():
            if position.quantity > 0 and symbol in historical_data:
                if current_date in historical_data[symbol].index:
                    current_price = historical_data[symbol].loc[current_date]['close']
                    position_value = position.quantity * current_price
                    equity_value += position_value
                    
                    # Update unrealized PnL
                    position.unrealized_pnl = position.quantity * (current_price - position.average_price)
        
        self.portfolio.total_value = self.portfolio.cash + equity_value
        
        # Calculate daily return
        if len(self.portfolio.daily_returns) == 0:
            daily_return = 0.0
        else:
            previous_value = self.initial_capital
            if len(self.portfolio.daily_returns) > 0:
                # Calculate previous total value
                previous_value = self.initial_capital * (1 + sum(self.portfolio.daily_returns))
            
            daily_return = (self.portfolio.total_value - previous_value) / previous_value
        
        self.portfolio.daily_returns.append(daily_return)
    
    def _calculate_performance_metrics(self) -> BacktestMetrics:
        """Calculate comprehensive performance metrics"""
        
        metrics = BacktestMetrics()
        
        if not self.portfolio.daily_returns or len(self.portfolio.daily_returns) < 2:
            return metrics
        
        returns = np.array(self.portfolio.daily_returns)
        
        # Basic metrics
        metrics.total_return = (self.portfolio.total_value - self.initial_capital) / self.initial_capital
        metrics.total_trades = len(self.portfolio.trades)
        
        # Annualized return
        days = len(returns)
        if days > 0:
            metrics.annualized_return = (1 + metrics.total_return) ** (252 / days) - 1
        
        # Volatility
        metrics.volatility = np.std(returns) * np.sqrt(252)
        
        # Sharpe ratio (assuming 0% risk-free rate)
        if metrics.volatility > 0:
            metrics.sharpe_ratio = metrics.annualized_return / metrics.volatility
        
        # Maximum drawdown
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        metrics.max_drawdown = abs(np.min(drawdowns))
        
        # Calmar ratio
        if metrics.max_drawdown > 0:
            metrics.calmar_ratio = metrics.annualized_return / metrics.max_drawdown
        
        # Sortino ratio
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0:
            downside_volatility = np.std(negative_returns) * np.sqrt(252)
            if downside_volatility > 0:
                metrics.sortino_ratio = metrics.annualized_return / downside_volatility
        
        # Trade-specific metrics
        if metrics.total_trades > 0:
            profitable_trades = []
            losing_trades = []
            
            # Calculate trade PnL
            for trade in self.portfolio.trades:
                if trade.action == "sell":
                    # Find corresponding buy trade(s)
                    buy_trades = [t for t in self.portfolio.trades 
                                if t.symbol == trade.symbol and t.action == "buy" and t.timestamp <= trade.timestamp]
                    
                    if buy_trades:
                        # Use FIFO for simplicity
                        buy_trade = buy_trades[-1]
                        trade_pnl = (trade.price - buy_trade.price) * trade.quantity - trade.commission - buy_trade.commission
                        
                        if trade_pnl > 0:
                            profitable_trades.append(trade_pnl)
                        else:
                            losing_trades.append(abs(trade_pnl))
            
            metrics.profitable_trades = len(profitable_trades)
            metrics.losing_trades = len(losing_trades)
            
            if metrics.total_trades > 0:
                metrics.win_rate = metrics.profitable_trades / (metrics.profitable_trades + metrics.losing_trades)
            
            if profitable_trades:
                metrics.avg_win = np.mean(profitable_trades)
                metrics.largest_win = max(profitable_trades)
            
            if losing_trades:
                metrics.avg_loss = np.mean(losing_trades)
                metrics.largest_loss = max(losing_trades)
            
            # Profit factor
            total_profits = sum(profitable_trades) if profitable_trades else 0
            total_losses = sum(losing_trades) if losing_trades else 0
            if total_losses > 0:
                metrics.profit_factor = total_profits / total_losses
        
        return metrics
    
    def _trade_to_dict(self, trade: BacktestTrade) -> Dict[str, Any]:
        """Convert trade to dictionary for serialization"""
        return {
            "timestamp": trade.timestamp.isoformat(),
            "symbol": trade.symbol,
            "action": trade.action,
            "quantity": trade.quantity,
            "price": trade.price,
            "commission": trade.commission,
            "strategy_id": trade.strategy_id,
            "signal_reason": trade.signal_reason
        }

class StrategyOptimizer:
    """Optimize strategy parameters using backtesting"""
    
    def __init__(self, backtesting_engine: BacktestingEngine):
        self.backtesting_engine = backtesting_engine
    
    async def optimize_parameters(
        self,
        strategy_class: type,
        base_parameters: Dict[str, Any],
        parameter_ranges: Dict[str, List],
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        optimization_metric: str = "sharpe_ratio"
    ) -> Dict[str, Any]:
        """Optimize strategy parameters using grid search"""
        
        logger.info(f"Starting parameter optimization for {strategy_class.__name__}")
        
        best_params = None
        best_score = float('-inf')
        all_results = []
        
        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations(parameter_ranges)
        
        logger.info(f"Testing {len(param_combinations)} parameter combinations")
        
        for i, param_combo in enumerate(param_combinations):
            try:
                # Merge base parameters with current combination
                test_params = {**base_parameters, **param_combo}
                
                # Create strategy instance
                strategy = strategy_class(f"optimization_test_{i}", test_params)
                
                # Run backtest
                results = await self.backtesting_engine.run_backtest(
                    strategy, symbols, start_date, end_date
                )
                
                # Get optimization score
                score = results["metrics"].get(optimization_metric, float('-inf'))
                
                # Track results
                result_entry = {
                    "parameters": test_params,
                    "score": score,
                    "metrics": results["metrics"]
                }
                all_results.append(result_entry)
                
                # Update best if better
                if score > best_score:
                    best_score = score
                    best_params = test_params
                
                logger.info(f"Combination {i+1}/{len(param_combinations)}: {optimization_metric}={score:.4f}")
                
            except Exception as e:
                logger.error(f"Error testing parameter combination {i}: {str(e)}")
        
        logger.info(f"Optimization completed. Best {optimization_metric}: {best_score:.4f}")
        
        return {
            "best_parameters": best_params,
            "best_score": best_score,
            "optimization_metric": optimization_metric,
            "all_results": sorted(all_results, key=lambda x: x["score"], reverse=True)
        }
    
    def _generate_parameter_combinations(self, parameter_ranges: Dict[str, List]) -> List[Dict[str, Any]]:
        """Generate all combinations of parameters"""
        
        import itertools
        
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        
        combinations = []
        for combo in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combo))
            combinations.append(param_dict)
        
        return combinations

# Global backtesting engine instance
backtesting_engine = BacktestingEngine()
strategy_optimizer = StrategyOptimizer(backtesting_engine)