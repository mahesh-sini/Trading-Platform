import { apiService } from './api';

export interface AutoTradingStatus {
  enabled: boolean;
  mode: string;
  subscription_plan: string;
  daily_limit: number;
  trades_today: number;
  remaining_trades: number;
  successful_trades_today: number;
  is_market_open: boolean;
  has_active_session: boolean;
  primary_broker_connected: boolean;
}

export interface AutoTradingSettings {
  enabled: boolean;
  mode: string;
}

export interface AutoTrade {
  id: string;
  date: string;
  time: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  executed_price?: number;
  total_value: number;
  confidence: number;
  expected_return: number;
  realized_pnl?: number;
  status: string;
  reason: string;
  execution_time?: string;
}

export interface AutoTradingHistoryParams {
  limit?: number;
  offset?: number;
  status_filter?: string;
  symbol?: string;
  start_date?: string;
  end_date?: string;
}

export interface AutoTradingAnalytics {
  period_days: number;
  total_trades: number;
  successful_trades: number;
  failed_trades: number;
  success_rate: number;
  total_pnl: number;
  average_return: number;
  average_confidence: number;
  most_traded_symbols: Array<{ symbol: string; count: number }>;
  daily_trade_count: Array<{ date: string; count: number }>;
}

export interface MarketStatus {
  is_market_open: boolean;
  market_hours: {
    nse: {
      open: string;
      close: string;
      timezone: string;
    };
    bse: {
      open: string;
      close: string;
      timezone: string;
    };
  };
  message: string;
}

class AutoTradingService {
  private readonly basePath = '/v1/auto-trading';

  async getStatus(): Promise<AutoTradingStatus> {
    const response = await apiService.get(`${this.basePath}/status`);
    return response.data;
  }

  async enable(settings: AutoTradingSettings): Promise<{ message: string; enabled: boolean; mode: string }> {
    const response = await apiService.post(`${this.basePath}/enable`, settings);
    return response.data;
  }

  async disable(): Promise<{ message: string; enabled: boolean }> {
    const response = await apiService.post(`${this.basePath}/disable`);
    return response.data;
  }

  async updateSettings(settings: AutoTradingSettings): Promise<{ message: string; enabled: boolean; mode: string }> {
    const response = await apiService.put(`${this.basePath}/settings`, settings);
    return response.data;
  }

  async getHistory(params: AutoTradingHistoryParams = {}): Promise<AutoTrade[]> {
    const queryParams = new URLSearchParams();
    
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.offset) queryParams.append('offset', params.offset.toString());
    if (params.status_filter) queryParams.append('status_filter', params.status_filter);
    if (params.symbol) queryParams.append('symbol', params.symbol);
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);

    const response = await apiService.get(`${this.basePath}/trades?${queryParams.toString()}`);
    return response.data;
  }

  async getAnalytics(days: number = 30): Promise<AutoTradingAnalytics> {
    const response = await apiService.get(`${this.basePath}/analytics?days=${days}`);
    return response.data;
  }

  async getMarketStatus(): Promise<MarketStatus> {
    const response = await apiService.get(`${this.basePath}/market-status`);
    return response.data;
  }

  // Manual intervention methods
  async emergencyStop(reason: string = 'Manual intervention'): Promise<{ message: string; status: string }> {
    const response = await apiService.post(`${this.basePath}/emergency-stop`, { reason });
    return response.data;
  }

  async pauseTrading(durationMinutes: number = 30, reason: string = 'Manual pause'): Promise<{ message: string; status: string }> {
    const response = await apiService.post(`${this.basePath}/pause`, {
      duration_minutes: durationMinutes,
      reason
    });
    return response.data;
  }

  async resumeTrading(): Promise<{ message: string; status: string }> {
    const response = await apiService.post(`${this.basePath}/resume`);
    return response.data;
  }
}

export const autoTradingService = new AutoTradingService();