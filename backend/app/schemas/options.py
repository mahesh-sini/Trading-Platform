"""
Pydantic schemas for Options Trading
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, validator
from datetime import datetime
from decimal import Decimal


class OptionsContractBase(BaseModel):
    symbol: str
    underlying_symbol: str
    option_type: str = Field(..., pattern=r"^(call|put)$")
    strike_price: Decimal
    expiration_date: datetime
    contract_size: int = 100


class OptionsContractResponse(OptionsContractBase):
    id: str
    last_price: Optional[Decimal]
    bid: Optional[Decimal]
    ask: Optional[Decimal]
    bid_size: Optional[int]
    ask_size: Optional[int]
    volume: int
    open_interest: int
    delta: Optional[Decimal]
    gamma: Optional[Decimal]
    theta: Optional[Decimal]
    vega: Optional[Decimal]
    rho: Optional[Decimal]
    implied_volatility: Optional[Decimal]
    theoretical_price: Optional[Decimal]
    intrinsic_value: Optional[Decimal]
    time_value: Optional[Decimal]
    time_to_expiration: Optional[Decimal]
    status: str
    exchange: Optional[str]
    last_trade_time: Optional[datetime]
    
    class Config:
        from_attributes = True


class OptionsChainResponse(BaseModel):
    underlying_symbol: str
    underlying_price: Decimal
    expiration_date: datetime
    calls: List[OptionsContractResponse]
    puts: List[OptionsContractResponse]
    total_call_volume: int
    total_put_volume: int
    put_call_ratio: Optional[Decimal]


class OptionsPositionBase(BaseModel):
    contract_id: str
    quantity: int
    average_price: Decimal


class OptionsPositionCreate(OptionsPositionBase):
    portfolio_id: str


class OptionsPositionResponse(OptionsPositionBase):
    id: str
    organization_id: str
    user_id: str
    portfolio_id: str
    cost_basis: Decimal
    current_price: Optional[Decimal]
    market_value: Optional[Decimal]
    unrealized_pnl: Decimal
    unrealized_pnl_percent: Decimal
    day_change: Decimal
    day_change_percent: Decimal
    position_delta: Optional[Decimal]
    position_gamma: Optional[Decimal]
    position_theta: Optional[Decimal]
    position_vega: Optional[Decimal]
    position_rho: Optional[Decimal]
    max_profit: Optional[Decimal]
    max_loss: Optional[Decimal]
    breakeven_price: Optional[Decimal]
    is_active: bool
    opened_at: datetime
    closed_at: Optional[datetime]
    contract: OptionsContractResponse
    
    class Config:
        from_attributes = True


class OptionsOrderBase(BaseModel):
    contract_symbol: str
    portfolio_id: str
    side: str = Field(..., pattern=r"^(buy_to_open|sell_to_open|buy_to_close|sell_to_close)$")
    quantity: int = Field(..., gt=0)
    order_type: str = Field(..., pattern=r"^(market|limit|stop|stop_limit)$")


class OptionsOrderCreate(OptionsOrderBase):
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    time_in_force: str = Field("DAY", pattern=r"^(DAY|GTC|IOC|FOK)$")
    
    @validator("limit_price")
    def validate_limit_price(cls, v, values):
        if values.get("order_type") in ["limit", "stop_limit"] and v is None:
            raise ValueError("Limit price required for limit orders")
        return v
    
    @validator("stop_price")
    def validate_stop_price(cls, v, values):
        if values.get("order_type") in ["stop", "stop_limit"] and v is None:
            raise ValueError("Stop price required for stop orders")
        return v


class OptionsOrderResponse(OptionsOrderBase):
    id: str
    organization_id: str
    user_id: str
    order_id: str
    client_order_id: Optional[str]
    limit_price: Optional[Decimal]
    stop_price: Optional[Decimal]
    filled_price: Optional[Decimal]
    time_in_force: str
    status: str
    filled_quantity: int
    remaining_quantity: Optional[int]
    commission: Decimal
    fees: Decimal
    total_cost: Optional[Decimal]
    strategy_id: Optional[str]
    leg_number: Optional[int]
    buying_power_effect: Optional[Decimal]
    margin_requirement: Optional[Decimal]
    placed_at: datetime
    filled_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    expires_at: Optional[datetime]
    broker_order_id: Optional[str]
    exchange: Optional[str]
    contract: OptionsContractResponse
    
    class Config:
        from_attributes = True


class OptionsStrategyLeg(BaseModel):
    option_type: str = Field(..., pattern=r"^(call|put|stock)$")
    side: str = Field(..., pattern=r"^(long|short)$")
    quantity: int = Field(..., gt=0)
    strike_price: Optional[Decimal] = None
    expiration_date: Optional[str] = None
    symbol: Optional[str] = None
    premium_paid: Optional[Decimal] = None


class OptionsStrategyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: str
    underlying_symbol: str
    description: Optional[str] = None
    legs: List[OptionsStrategyLeg]


class OptionsStrategyCreate(OptionsStrategyBase):
    portfolio_id: str
    market_outlook: Optional[str] = Field(None, pattern=r"^(bullish|bearish|neutral|volatile)$")
    profit_target: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None


class OptionsStrategyResponse(OptionsStrategyBase):
    id: str
    organization_id: str
    user_id: str
    portfolio_id: str
    market_outlook: Optional[str]
    profit_target: Optional[Decimal]
    stop_loss: Optional[Decimal]
    max_profit: Optional[Decimal]
    max_loss: Optional[Decimal]
    breakeven_points: Optional[List[Decimal]]
    net_delta: Optional[Decimal]
    net_gamma: Optional[Decimal]
    net_theta: Optional[Decimal]
    net_vega: Optional[Decimal]
    net_rho: Optional[Decimal]
    current_value: Optional[Decimal]
    cost_basis: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]
    unrealized_pnl_percent: Optional[Decimal]
    status: str
    is_paper_trade: bool
    created_at: datetime
    updated_at: Optional[datetime]
    closed_at: Optional[datetime]
    expiration_date: Optional[datetime]
    
    class Config:
        from_attributes = True


class GreeksResponse(BaseModel):
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class PayoffPoint(BaseModel):
    underlying_price: float
    payoff: float


class StrategyAnalysisResponse(BaseModel):
    strategy_id: str
    underlying_price: float
    payoff_diagram: List[PayoffPoint]
    breakeven_points: List[float]
    max_profit: Optional[float]
    max_loss: Optional[float]
    greeks: GreeksResponse


class VolatilitySurfacePoint(BaseModel):
    strike_price: Decimal
    expiration_date: datetime
    implied_volatility: Decimal
    delta: Optional[Decimal]


class VolatilitySurfaceResponse(BaseModel):
    underlying_symbol: str
    underlying_price: Decimal
    data_timestamp: datetime
    surface_points: List[VolatilitySurfacePoint]


class OptionsRiskMetrics(BaseModel):
    portfolio_delta: Decimal
    portfolio_gamma: Decimal
    portfolio_theta: Decimal
    portfolio_vega: Decimal
    portfolio_rho: Decimal
    var_95: Optional[Decimal]  # Value at Risk (95%)
    expected_shortfall: Optional[Decimal]
    max_loss_1day: Optional[Decimal]
    stress_test_results: Optional[Dict[str, Decimal]]


class OptionsPortfolioSummary(BaseModel):
    total_positions: int
    total_market_value: Decimal
    total_unrealized_pnl: Decimal
    total_day_change: Decimal
    active_strategies: int
    pending_orders: int
    risk_metrics: OptionsRiskMetrics
    top_positions: List[OptionsPositionResponse]


class ImpliedVolatilityRequest(BaseModel):
    underlying_symbol: str
    option_type: str = Field(..., pattern=r"^(call|put)$")
    strike_price: Decimal
    expiration_date: datetime
    market_price: Decimal
    underlying_price: Decimal


class ImpliedVolatilityResponse(BaseModel):
    implied_volatility: Optional[Decimal]
    calculation_method: str = "newton_raphson"
    iterations: Optional[int]
    error: Optional[str]


class OptionsPricingRequest(BaseModel):
    underlying_symbol: str
    option_type: str = Field(..., pattern=r"^(call|put)$")
    strike_price: Decimal
    expiration_date: datetime
    underlying_price: Decimal
    volatility: Decimal
    risk_free_rate: Optional[Decimal] = Field(0.05, ge=0, le=1)
    dividend_yield: Optional[Decimal] = Field(0.0, ge=0, le=1)


class OptionsPricingResponse(BaseModel):
    theoretical_price: Decimal
    intrinsic_value: Decimal
    time_value: Decimal
    greeks: GreeksResponse
    pricing_model: str = "black_scholes"


class StrategyBacktestRequest(BaseModel):
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Field(..., gt=0)
    rebalance_frequency: str = Field("weekly", pattern=r"^(daily|weekly|monthly)$")


class StrategyBacktestResult(BaseModel):
    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_value: Decimal
    total_return: Decimal
    total_return_percent: Decimal
    annualized_return: Decimal
    max_drawdown: Decimal
    sharpe_ratio: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    trades_executed: int
    daily_returns: List[Dict[str, Any]]


class OptionsScreenerRequest(BaseModel):
    underlying_symbols: Optional[List[str]] = None
    min_volume: Optional[int] = Field(None, ge=0)
    max_bid_ask_spread: Optional[Decimal] = Field(None, ge=0)
    min_delta: Optional[Decimal] = Field(None, ge=-1, le=1)
    max_delta: Optional[Decimal] = Field(None, ge=-1, le=1)
    min_implied_volatility: Optional[Decimal] = Field(None, ge=0)
    max_implied_volatility: Optional[Decimal] = Field(None, ge=0)
    min_time_to_expiration: Optional[int] = Field(None, ge=0)  # days
    max_time_to_expiration: Optional[int] = Field(None, ge=0)  # days
    option_type: Optional[str] = Field(None, pattern=r"^(call|put)$")
    moneyness_range: Optional[Tuple[Decimal, Decimal]] = None  # (min, max) moneyness


class OptionsScreenerResult(BaseModel):
    contracts: List[OptionsContractResponse]
    total_results: int
    filters_applied: Dict[str, Any]


class OrderExecutionReport(BaseModel):
    order_id: str
    execution_id: str
    execution_price: Decimal
    execution_quantity: int
    execution_time: datetime
    commission: Decimal
    fees: Decimal
    exchange: str
    liquidity_flag: Optional[str]  # "add" or "remove"