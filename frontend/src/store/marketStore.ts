import { create } from 'zustand';
import { Quote, HistoricalDataPoint, NewsItem, SymbolInfo } from '@/types';

interface MarketState {
  quotes: Record<string, Quote>;
  historicalData: Record<string, HistoricalDataPoint[]>;
  news: NewsItem[];
  symbolInfo: Record<string, SymbolInfo>;
  watchlist: string[];
  subscriptions: Set<string>;
  isLoading: boolean;
  error: string | null;
}

interface MarketActions {
  // Quote actions
  updateQuote: (symbol: string, quote: Quote) => void;
  getQuote: (symbol: string) => Promise<Quote | null>;
  subscribeToQuote: (symbol: string) => void;
  unsubscribeFromQuote: (symbol: string) => void;
  
  // Historical data actions
  setHistoricalData: (symbol: string, data: HistoricalDataPoint[]) => void;
  getHistoricalData: (symbol: string, period?: string, interval?: string) => Promise<HistoricalDataPoint[]>;
  
  // News actions
  setNews: (news: NewsItem[]) => void;
  getNews: (symbol?: string, limit?: number) => Promise<NewsItem[]>;
  
  // Symbol info actions
  setSymbolInfo: (symbol: string, info: SymbolInfo) => void;
  getSymbolInfo: (symbol: string) => Promise<SymbolInfo | null>;
  
  // Watchlist actions
  addToWatchlist: (symbol: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  setWatchlist: (symbols: string[]) => void;
  
  // Utility actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

type MarketStore = MarketState & MarketActions;

const initialState: MarketState = {
  quotes: {},
  historicalData: {},
  news: [],
  symbolInfo: {},
  watchlist: [],
  subscriptions: new Set(),
  isLoading: false,
  error: null,
};

export const useMarketStore = create<MarketStore>((set, get) => ({
  ...initialState,

  // Quote actions
  updateQuote: (symbol: string, quote: Quote) => {
    set((state) => ({
      quotes: {
        ...state.quotes,
        [symbol]: quote,
      },
    }));
  },

  getQuote: async (symbol: string) => {
    try {
      set({ isLoading: true, error: null });
      
      const response = await fetch(`/api/market-data/quote/${symbol}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch quote');
      }
      
      const quote = await response.json();
      
      set((state) => ({
        quotes: {
          ...state.quotes,
          [symbol]: quote,
        },
        isLoading: false,
      }));
      
      return quote;
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch quote',
      });
      return null;
    }
  },

  subscribeToQuote: (symbol: string) => {
    set((state) => ({
      subscriptions: new Set([...state.subscriptions, symbol]),
    }));
  },

  unsubscribeFromQuote: (symbol: string) => {
    set((state) => {
      const newSubscriptions = new Set(state.subscriptions);
      newSubscriptions.delete(symbol);
      return { subscriptions: newSubscriptions };
    });
  },

  // Historical data actions
  setHistoricalData: (symbol: string, data: HistoricalDataPoint[]) => {
    set((state) => ({
      historicalData: {
        ...state.historicalData,
        [symbol]: data,
      },
    }));
  },

  getHistoricalData: async (symbol: string, period = '1y', interval = '1d') => {
    try {
      set({ isLoading: true, error: null });
      
      const response = await fetch(
        `/api/market-data/history/${symbol}?period=${period}&interval=${interval}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch historical data');
      }
      
      const result = await response.json();
      const data = result.data;
      
      set((state) => ({
        historicalData: {
          ...state.historicalData,
          [symbol]: data,
        },
        isLoading: false,
      }));
      
      return data;
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch historical data',
      });
      return [];
    }
  },

  // News actions
  setNews: (news: NewsItem[]) => {
    set({ news });
  },

  getNews: async (symbol?: string, limit = 50) => {
    try {
      set({ isLoading: true, error: null });
      
      const url = symbol
        ? `/api/news/symbol/${symbol}?limit=${limit}`
        : `/api/news/latest?limit=${limit}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Failed to fetch news');
      }
      
      const result = await response.json();
      const news = result.news;
      
      set({ news, isLoading: false });
      
      return news;
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch news',
      });
      return [];
    }
  },

  // Symbol info actions
  setSymbolInfo: (symbol: string, info: SymbolInfo) => {
    set((state) => ({
      symbolInfo: {
        ...state.symbolInfo,
        [symbol]: info,
      },
    }));
  },

  getSymbolInfo: async (symbol: string) => {
    try {
      set({ isLoading: true, error: null });
      
      const response = await fetch(`/api/market-data/info/${symbol}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch symbol info');
      }
      
      const info = await response.json();
      
      set((state) => ({
        symbolInfo: {
          ...state.symbolInfo,
          [symbol]: info,
        },
        isLoading: false,
      }));
      
      return info;
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch symbol info',
      });
      return null;
    }
  },

  // Watchlist actions
  addToWatchlist: (symbol: string) => {
    set((state) => ({
      watchlist: [...state.watchlist, symbol],
    }));
  },

  removeFromWatchlist: (symbol: string) => {
    set((state) => ({
      watchlist: state.watchlist.filter((s) => s !== symbol),
    }));
  },

  setWatchlist: (symbols: string[]) => {
    set({ watchlist: symbols });
  },

  // Utility actions
  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  clearError: () => {
    set({ error: null });
  },
}));