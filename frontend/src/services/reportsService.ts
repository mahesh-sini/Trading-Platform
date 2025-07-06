import { apiService } from './api';

export interface ReportSummary {
  period_start: string;
  period_end: string;
  total_trades: number;
  successful_trades: number;
  failed_trades: number;
  total_volume: number;
  total_pnl: number;
  success_rate: number;
  average_trade_size: number;
  best_performing_symbol?: string;
  worst_performing_symbol?: string;
}

export interface ReportFilters {
  start_date?: string;
  end_date?: string;
  symbols?: string[];
  status?: string;
  trade_type?: 'auto' | 'manual' | 'all';
  min_amount?: number;
  max_amount?: number;
}

export interface DetailedTradeReport {
  summary: ReportSummary;
  trades: Array<{
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
  }>;
  daily_breakdown: Array<{
    date: string;
    total_trades: number;
    successful_trades: number;
    total_volume: number;
    total_pnl: number;
  }>;
  symbol_breakdown: Array<{
    symbol: string;
    total_trades: number;
    successful_trades: number;
    total_volume: number;
    total_pnl: number;
    avg_confidence: number;
  }>;
}

export interface EODSummary {
  date: string;
  auto_trading: {
    total_trades: number;
    executed_trades: number;
    failed_trades: number;
    total_volume: number;
    realized_pnl: number;
    success_rate: number;
    symbols_traded: string[];
  };
  manual_trading: {
    total_trades: number;
    total_volume: number;
    estimated_pnl: number;
  };
  overall: {
    total_trades: number;
    total_volume: number;
    total_pnl: number;
  };
  generated_at: string;
}

export interface PerformanceMetrics {
  period_days: number;
  total_trades: number;
  metrics: {
    total_return: number;
    average_return_per_trade: number;
    win_rate: number;
    average_win: number;
    average_loss: number;
    profit_factor: number | string;
    average_confidence: number;
    best_trade: number;
    worst_trade: number;
    total_winning_trades: number;
    total_losing_trades: number;
  };
}

export interface ExportParams {
  format: 'csv' | 'json';
  start_date?: string;
  end_date?: string;
  symbols?: string;
  status?: string;
}

class ReportsService {
  private readonly basePath = '/v1/reports';

  async getAutoTradesSummary(
    startDate?: string,
    endDate?: string
  ): Promise<ReportSummary> {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await apiService.get(
      `${this.basePath}/auto-trades/summary?${params.toString()}`
    );
    return response.data;
  }

  async getDetailedAutoTradesReport(
    filters: ReportFilters
  ): Promise<DetailedTradeReport> {
    const response = await apiService.post(
      `${this.basePath}/auto-trades/detailed`,
      filters
    );
    return response.data;
  }

  async exportAutoTrades(params: ExportParams): Promise<void> {
    const queryParams = new URLSearchParams();
    queryParams.append('format', params.format);
    if (params.start_date) queryParams.append('start_date', params.start_date);
    if (params.end_date) queryParams.append('end_date', params.end_date);
    if (params.symbols) queryParams.append('symbols', params.symbols);
    if (params.status) queryParams.append('status', params.status);

    const response = await apiService.get(
      `${this.basePath}/auto-trades/export?${queryParams.toString()}`,
      {
        responseType: 'blob'
      }
    );

    // Handle file download
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    const startStr = params.start_date || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    const endStr = params.end_date || new Date().toISOString().split('T')[0];
    link.download = `auto_trades_report_${startStr}_${endStr}.${params.format}`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  async getEODSummary(tradeDate?: string): Promise<EODSummary> {
    const params = new URLSearchParams();
    if (tradeDate) params.append('trade_date', tradeDate);

    const response = await apiService.get(
      `${this.basePath}/eod-summary?${params.toString()}`
    );
    return response.data;
  }

  async getPerformanceMetrics(periodDays: number = 30): Promise<PerformanceMetrics> {
    const response = await apiService.get(
      `${this.basePath}/performance-metrics?period_days=${periodDays}`
    );
    return response.data;
  }

  // Utility methods for report generation
  generateDateRange(days: number): { startDate: string; endDate: string } {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    };
  }

  formatCurrency(value: number, currency: string = 'INR'): string {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(value);
  }

  formatPercentage(value: number, decimals: number = 2): string {
    return `${value.toFixed(decimals)}%`;
  }

  calculateSuccessRate(successful: number, total: number): number {
    return total > 0 ? (successful / total) * 100 : 0;
  }
}

export const reportsService = new ReportsService();