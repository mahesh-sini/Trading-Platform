// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

// User Types
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  subscription_tier: SubscriptionTier;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export enum SubscriptionTier {
  FREE = 'free',
  BASIC = 'basic',
  PRO = 'pro',
  ENTERPRISE = 'enterprise'
}

// Authentication Types
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

// Market Data Types
export interface Quote {
  symbol: string;
  price: number;
  bid: number;
  ask: number;
  volume: number;
  change: number;
  change_percent: number;
  market_status: string;
  timestamp: string;
}

export interface HistoricalDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SymbolInfo {
  symbol: string;
  company_name: string;
  exchange: string;
  sector: string;
  industry: string;
  market_cap: number;
  shares_outstanding: number;
}

// Trading Types
export interface Position {
  id: string;
  symbol: string;
  quantity: number;
  average_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  quantity: number;
  price?: number;
  status: OrderStatus;
  filled_quantity: number;
  average_fill_price?: number;
  created_at: string;
  updated_at: string;
}

export enum OrderSide {
  BUY = 'buy',
  SELL = 'sell'
}

export enum OrderType {
  MARKET = 'market',
  LIMIT = 'limit',
  STOP = 'stop',
  STOP_LIMIT = 'stop_limit'
}

export enum OrderStatus {
  PENDING = 'pending',
  FILLED = 'filled',
  PARTIALLY_FILLED = 'partially_filled',
  CANCELLED = 'cancelled',
  REJECTED = 'rejected'
}

// Portfolio Types
export interface Portfolio {
  id: string;
  name: string;
  total_value: number;
  cash_balance: number;
  equity_value: number;
  day_change: number;
  day_change_percent: number;
  total_return: number;
  total_return_percent: number;
  positions: Position[];
  updated_at: string;
}

// ML Prediction Types
export interface Prediction {
  id: string;
  symbol: string;
  prediction_type: PredictionType;
  predicted_price: number;
  confidence: number;
  horizon: string;
  features_used: string[];
  created_at: string;
  expires_at: string;
}

export enum PredictionType {
  PRICE = 'price',
  TREND = 'trend',
  VOLATILITY = 'volatility'
}

// Strategy Types
export interface Strategy {
  id: string;
  name: string;
  description: string;
  strategy_type: StrategyType;
  parameters: Record<string, any>;
  is_active: boolean;
  performance_metrics: PerformanceMetrics;
  created_at: string;
  updated_at: string;
}

export enum StrategyType {
  MEAN_REVERSION = 'mean_reversion',
  MOMENTUM = 'momentum',
  ARBITRAGE = 'arbitrage',
  ML_BASED = 'ml_based'
}

export interface PerformanceMetrics {
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
}

// News Types
export interface NewsItem {
  headline: string;
  summary: string;
  url: string;
  source: string;
  published_at: string;
  symbols: string[];
  sentiment_score?: number;
}

// Watchlist Types
export interface Watchlist {
  id: string;
  name: string;
  symbols: string[];
  created_at: string;
  updated_at: string;
}

// WebSocket Types
export interface WebSocketMessage {
  type: string;
  symbol?: string;
  data: any;
  timestamp?: string;
}

// Chart Types
export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string;
  borderColor?: string;
  borderWidth?: number;
}

// Component Props Types
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
}

// Form Types
export interface FormError {
  field: string;
  message: string;
}

// Navigation Types
export interface NavigationItem {
  name: string;
  href: string;
  icon?: React.ComponentType<{ className?: string }>;
  current?: boolean;
}

// Dashboard Types
export interface DashboardMetrics {
  portfolio_value: number;
  day_change: number;
  day_change_percent: number;
  total_return: number;
  total_return_percent: number;
  active_positions: number;
  pending_orders: number;
  watchlist_alerts: number;
}