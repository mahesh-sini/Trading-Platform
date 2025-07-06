// Trading Platform Type Definitions

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'user' | 'admin' | 'trader';
  createdAt: string;
  lastLogin?: string;
  isActive: boolean;
}

export interface Portfolio {
  id: string;
  userId: string;
  totalValue: number;
  cash: number;
  equity: number;
  dayChange: number;
  dayChangePercent: number;
  positions: Position[];
  performance: PortfolioPerformance;
  updatedAt: string;
}

export interface Position {
  id: string;
  symbol: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  marketValue: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  realizedPnl: number;
  dayChange: number;
  dayChangePercent: number;
  openDate: string;
  sector?: string;
  industry?: string;
}

export interface PortfolioPerformance {
  totalReturn: number;
  totalReturnPercent: number;
  annualizedReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  calmarRatio: number;
  sortinoRatio: number;
}

export interface Trade {
  id: string;
  userId: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  totalValue: number;
  commission: number;
  status: 'pending' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected';
  orderType: 'market' | 'limit' | 'stop' | 'stop_limit';
  timeInForce: 'day' | 'gtc' | 'ioc' | 'fok';
  strategyId?: string;
  executedAt?: string;
  createdAt: string;
  filledQuantity?: number;
  avgFillPrice?: number;
  reason?: string;
}

export interface Order {
  id: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  price?: number;
  stopPrice?: number;
  orderType: 'market' | 'limit' | 'stop' | 'stop_limit';
  timeInForce: 'day' | 'gtc' | 'ioc' | 'fok';
  status: 'pending' | 'open' | 'filled' | 'partially_filled' | 'cancelled' | 'rejected';
  createdAt: string;
  updatedAt: string;
  filledQuantity: number;
  avgFillPrice?: number;
  totalValue: number;
  commission: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  previousClose: number;
  marketCap?: number;
  peRatio?: number;
  week52High?: number;
  week52Low?: number;
  avgVolume?: number;
  bid?: number;
  ask?: number;
  bidSize?: number;
  askSize?: number;
  timestamp: string;
}

export interface MarketQuote {
  symbol: string;
  bid: number;
  ask: number;
  bidSize: number;
  askSize: number;
  last: number;
  lastSize: number;
  volume: number;
  timestamp: string;
}

export interface OHLCV {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  strategyType: 'momentum' | 'mean_reversion' | 'ml_based' | 'custom';
  parameters: Record<string, any>;
  isActive: boolean;
  performance: StrategyPerformance;
  createdAt: string;
  updatedAt: string;
}

export interface StrategyPerformance {
  totalReturn: number;
  totalReturnPercent: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  profitableTrades: number;
  avgWin: number;
  avgLoss: number;
  profitFactor: number;
  avgConfidence: number;
}

export interface TradingSignal {
  id: string;
  strategyId: string;
  symbol: string;
  signal: 'buy' | 'sell' | 'hold';
  confidence: number;
  price: number;
  quantity: number;
  reason: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface BacktestResult {
  strategyId: string;
  period: {
    startDate: string;
    endDate: string;
    durationDays: number;
  };
  initialCapital: number;
  finalValue: number;
  metrics: {
    totalReturn: number;
    annualizedReturn: number;
    volatility: number;
    sharpeRatio: number;
    maxDrawdown: number;
    winRate: number;
    profitFactor: number;
    totalTrades: number;
    calmarRatio: number;
    sortinoRatio: number;
  };
  trades: Trade[];
  dailyReturns: number[];
  equityCurve: Array<{ date: string; value: number }>;
}

export interface Alert {
  id: string;
  type: 'price' | 'volume' | 'technical' | 'news' | 'risk';
  severity: 'info' | 'warning' | 'error' | 'critical';
  title: string;
  message: string;
  symbol?: string;
  condition: string;
  isActive: boolean;
  triggeredAt?: string;
  createdAt: string;
  metadata?: Record<string, any>;
}

export interface RiskMetrics {
  portfolioValue: number;
  exposure: number;
  exposurePercent: number;
  var95: number;
  var99: number;
  expectedShortfall: number;
  beta: number;
  maxPositionSize: number;
  concentration: Record<string, number>;
  sectorExposure: Record<string, number>;
}

export interface PerformanceMetrics {
  period: '1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | 'YTD' | 'ALL';
  totalReturn: number;
  totalReturnPercent: number;
  benchmarkReturn?: number;
  alpha?: number;
  beta?: number;
  sharpeRatio: number;
  informationRatio?: number;
  treynorRatio?: number;
  calmarRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  volatility: number;
  downside_volatility: number;
  averageReturn: number;
  winRate: number;
  bestDay: number;
  worstDay: number;
}

export interface TechnicalIndicator {
  name: string;
  value: number;
  signal: 'bullish' | 'bearish' | 'neutral';
  strength: 'weak' | 'moderate' | 'strong';
  description: string;
}

export interface NewsItem {
  id: string;
  title: string;
  summary: string;
  content?: string;
  source: string;
  publishedAt: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  sentimentScore: number;
  symbols: string[];
  categories: string[];
  url?: string;
  imageUrl?: string;
}

export interface MLPrediction {
  symbol: string;
  predictedPrice: number;
  confidence: number;
  timeHorizon: string;
  features: Record<string, number>;
  modelName: string;
  timestamp: string;
}

export interface Watchlist {
  id: string;
  name: string;
  symbols: string[];
  createdAt: string;
  updatedAt: string;
  isDefault: boolean;
}

export interface DashboardWidget {
  id: string;
  type: 'portfolio_summary' | 'market_overview' | 'positions' | 'orders' | 'watchlist' | 'news' | 'performance_chart' | 'strategy_performance' | 'trading_chart' | 'order_form' | 'alerts';
  title: string;
  size: 'small' | 'medium' | 'large';
  position: { x: number; y: number; w: number; h: number };
  config: Record<string, any>;
  isVisible: boolean;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    [serviceName: string]: {
      status: 'healthy' | 'degraded' | 'unhealthy';
      lastCheck: string;
      responseTime: number;
    };
  };
  timestamp: string;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  timestamp: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// WebSocket Message Types
export interface WSMessage {
  type: 'market_data' | 'trade_update' | 'order_update' | 'alert' | 'system_update';
  data: any;
  timestamp: string;
}

export interface MarketDataUpdate {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: string;
}

// Form Types
export interface OrderFormData {
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  orderType: 'market' | 'limit' | 'stop' | 'stop_limit';
  price?: number;
  stopPrice?: number;
  timeInForce: 'day' | 'gtc' | 'ioc' | 'fok';
}

export interface StrategyFormData {
  name: string;
  description: string;
  strategyType: 'momentum' | 'mean_reversion' | 'ml_based';
  parameters: Record<string, any>;
  isActive: boolean;
}

export interface AlertFormData {
  type: 'price' | 'volume' | 'technical';
  symbol: string;
  condition: string;
  value: number;
  message: string;
}

// Chart Types
export interface ChartData {
  time: string;
  value: number;
}

export interface CandlestickData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export interface ChartConfig {
  timeframe: '1m' | '5m' | '15m' | '1h' | '4h' | '1d' | '1w' | '1M';
  indicators: string[];
  overlays: string[];
  style: 'candlestick' | 'line' | 'area' | 'heikin_ashi';
}

// Error Types
export interface TradingError {
  code: string;
  message: string;
  field?: string;
  details?: Record<string, any>;
}

// Stock Search Types
export interface Stock {
  symbol: string;
  name: string;
  exchange: 'NSE' | 'BSE' | 'NYSE' | 'NASDAQ';
  sector?: string;
  isin?: string;
  market_cap?: number;
  listing_date?: string;
  description?: string;
  price?: number;
  change?: number;
  changePercent?: number;
  volume?: number;
  last_updated?: string;
  // Financial data
  pe_ratio?: number;
  pb_ratio?: number;
  dividend_yield?: number;
  beta?: number;
  debt_to_equity?: number;
  roe?: number;
  roa?: number;
  earnings_growth?: number;
  revenue_growth?: number;
  book_value?: number;
  dividend_per_share?: number;
  last_dividend_date?: string;
  bonus_ratio?: string;
  split_ratio?: string;
  face_value?: number;
  // Enhanced metadata
  is_fo_enabled?: boolean;
  is_etf?: boolean;
  is_index?: boolean;
  lot_size?: number;
  tick_size?: number;
}

// Financial data interface for comprehensive display
export interface FinancialData {
  pe_ratio?: number;
  pb_ratio?: number;
  dividend_yield?: number;
  dividend_per_share?: number;
  last_dividend_date?: string;
  beta?: number;
  debt_to_equity?: number;
  roe?: number;
  roa?: number;
  earnings_growth?: number;
  revenue_growth?: number;
  book_value?: number;
  bonus_history?: Array<{
    date: string;
    ratio: string;
    description: string;
  }>;
  split_history?: Array<{
    date: string;
    ratio: string;
    old_face_value: number;
    new_face_value: number;
  }>;
  financial_summary?: {
    market_cap: number;
    enterprise_value?: number;
    shares_outstanding?: number;
    float_shares?: number;
    insider_ownership?: number;
    institutional_ownership?: number;
  };
}