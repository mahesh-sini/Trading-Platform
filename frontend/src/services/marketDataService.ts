/**
 * Live Market Data Service - Frontend
 * Replaces mock data with real API calls to live market data endpoints
 */

import { ApiClient } from './api';

export interface LiveQuote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  previous_close: number;
  bid: number;
  ask: number;
  timestamp: string;
  exchange: string;
  currency: string;
}

export interface HistoricalBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketIndex {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume?: number;
  data_source: 'live' | 'fallback';
}

export interface MarketMover {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface BatchQuotesResponse {
  quotes: Record<string, LiveQuote>;
  symbols_requested: string[];
  symbols_found: string[];
  errors: string[];
}

class MarketDataService {
  private apiClient: ApiClient;
  private subscriptions: Map<string, EventSource> = new Map();
  private eventListeners: Map<string, ((data: any) => void)[]> = new Map();

  constructor() {
    this.apiClient = new ApiClient();
  }

  /**
   * Get live quote for a single symbol
   * Replaces: Mock price data in dashboard components
   */
  async getLiveQuote(symbol: string, exchange: string = 'NSE'): Promise<LiveQuote | null> {
    try {
      const response = await this.apiClient.get(`/market/quote/${symbol}`, {
        params: { exchange }
      });
      
      if (response.success) {
        return response.data;
      }
      
      console.warn(`No live quote data for ${symbol}`);
      return null;
    } catch (error) {
      console.error(`Error fetching live quote for ${symbol}:`, error);
      return null;
    }
  }

  /**
   * Get live quotes for multiple symbols (optimized for watchlists)
   * Replaces: Mock watchlist data updates
   */
  async getBatchQuotes(symbols: string[], exchange: string = 'NSE'): Promise<BatchQuotesResponse> {
    try {
      const response = await this.apiClient.get('/market/quotes/batch', {
        params: { 
          symbols,  // FastAPI will handle the array properly
          exchange 
        }
      });
      
      if (response.success) {
        return response.data;
      }
      
      return {
        quotes: {},
        symbols_requested: symbols,
        symbols_found: [],
        errors: ['Failed to fetch batch quotes']
      };
    } catch (error) {
      console.error('Error fetching batch quotes:', error);
      return {
        quotes: {},
        symbols_requested: symbols,
        symbols_found: [],
        errors: [error instanceof Error ? error.message : 'Unknown error']
      };
    }
  }

  /**
   * Get live Indian market indices
   * Replaces: Mock indices data (NIFTY, SENSEX, BANKNIFTY)
   */
  async getIndices(): Promise<MarketIndex[]> {
    try {
      const response = await this.apiClient.get('/market/indices');
      
      if (response.success) {
        return response.data;
      }
      
      // Fallback to default values if API fails
      return this.getFallbackIndices();
    } catch (error) {
      console.error('Error fetching indices:', error);
      return this.getFallbackIndices();
    }
  }

  /**
   * Get historical data for charting
   * Replaces: Mock chart data in TradingChart component
   */
  async getHistoricalData(
    symbol: string,
    period: string = '1d',
    interval: string = '1d',
    exchange: string = 'NSE'
  ): Promise<HistoricalBar[]> {
    try {
      const response = await this.apiClient.get(`/market/historical/${symbol}`, {
        params: { period, interval, exchange }
      });
      
      if (response.success) {
        return response.data.bars;
      }
      
      return [];
    } catch (error) {
      console.error(`Error fetching historical data for ${symbol}:`, error);
      return [];
    }
  }

  /**
   * Get market movers (top gainers and losers)
   * Replaces: Mock market movers data
   */
  async getMarketMovers(): Promise<{ top_gainers: MarketMover[]; top_losers: MarketMover[] }> {
    try {
      const response = await this.apiClient.get('/market/market-movers');
      
      if (response.success) {
        return response.data;
      }
      
      // Fallback data
      return this.getFallbackMarketMovers();
    } catch (error) {
      console.error('Error fetching market movers:', error);
      return this.getFallbackMarketMovers();
    }
  }

  /**
   * Subscribe to real-time updates for symbols
   * Sets up Server-Sent Events streaming
   */
  async subscribeToRealTime(symbols: string[]): Promise<boolean> {
    try {
      const response = await this.apiClient.post('/market/subscribe', { symbols });
      return response.success;
    } catch (error) {
      console.error('Error subscribing to real-time updates:', error);
      return false;
    }
  }

  /**
   * Start streaming real-time data for a symbol
   * Alternative to WebSocket using Server-Sent Events
   */
  startStream(symbol: string, onData: (data: any) => void): void {
    try {
      // Close existing stream if any
      this.stopStream(symbol);

      const eventSource = new EventSource(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/market/stream/${symbol}?exchange=NSE`,
        { withCredentials: true }
      );

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onData(data);
        } catch (error) {
          console.error('Error parsing stream data:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error(`Stream error for ${symbol}:`, error);
        // Attempt to reconnect after 5 seconds
        setTimeout(() => {
          if (!this.subscriptions.has(symbol)) {
            this.startStream(symbol, onData);
          }
        }, 5000);
      };

      this.subscriptions.set(symbol, eventSource);

      // Store callback for later cleanup
      if (!this.eventListeners.has(symbol)) {
        this.eventListeners.set(symbol, []);
      }
      this.eventListeners.get(symbol)!.push(onData);

    } catch (error) {
      console.error(`Error starting stream for ${symbol}:`, error);
    }
  }

  /**
   * Stop streaming for a symbol
   */
  stopStream(symbol: string): void {
    const eventSource = this.subscriptions.get(symbol);
    if (eventSource) {
      eventSource.close();
      this.subscriptions.delete(symbol);
    }
    this.eventListeners.delete(symbol);
  }

  /**
   * Stop all active streams
   */
  stopAllStreams(): void {
    this.subscriptions.forEach((eventSource) => {
      eventSource.close();
    });
    this.subscriptions.clear();
    this.eventListeners.clear();
  }

  /**
   * Check service health
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.apiClient.get('/market/health');
      return response.success && response.data.service_status === 'healthy';
    } catch (error) {
      console.error('Market data service health check failed:', error);
      return false;
    }
  }

  /**
   * Fallback indices data when live data is unavailable
   */
  private getFallbackIndices(): MarketIndex[] {
    return [
      { symbol: 'NIFTY', price: 19674.25, change: 156.80, changePercent: 0.80, data_source: 'fallback' },
      { symbol: 'SENSEX', price: 65930.77, change: 442.65, changePercent: 0.68, data_source: 'fallback' },
      { symbol: 'BANKNIFTY', price: 43567.90, change: -234.50, changePercent: -0.53, data_source: 'fallback' }
    ];
  }

  /**
   * Fallback market movers when live data is unavailable
   */
  private getFallbackMarketMovers(): { top_gainers: MarketMover[]; top_losers: MarketMover[] } {
    return {
      top_gainers: [
        { symbol: 'ADANIGREEN', price: 1245.60, change: 8.5, changePercent: 8.5 },
        { symbol: 'TATAMOTORS', price: 567.80, change: 6.2, changePercent: 6.2 },
        { symbol: 'BAJFINANCE', price: 6789.45, change: 4.8, changePercent: 4.8 }
      ],
      top_losers: [
        { symbol: 'ZEEL', price: 234.50, change: -5.2, changePercent: -5.2 },
        { symbol: 'YESBANK', price: 18.65, change: -3.8, changePercent: -3.8 },
        { symbol: 'SUZLON', price: 12.40, change: -2.9, changePercent: -2.9 }
      ]
    };
  }
}

// Singleton instance
export const marketDataService = new MarketDataService();

// Hook for React components
export const useMarketData = () => {
  return marketDataService;
};

// Utility functions for common operations
export const formatPrice = (price: number, currency: string = 'INR'): string => {
  if (currency === 'INR') {
    return `₹${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export const formatChange = (change: number, changePercent: number): string => {
  const sign = change >= 0 ? '+' : '';
  return `${sign}${change.toFixed(2)} (${sign}${changePercent.toFixed(2)}%)`;
};

export const getChangeColor = (change: number): string => {
  return change >= 0 ? 'text-green-600' : 'text-red-600';
};