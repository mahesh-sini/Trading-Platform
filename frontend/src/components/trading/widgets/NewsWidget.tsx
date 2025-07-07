import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { NewsItem } from '@/types/trading';
import { useWebSocket } from '@/hooks/useWebSocket';
import { 
  NewspaperIcon, 
  ClockIcon, 
  ArrowTopRightOnSquareIcon,
  FunnelIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { format, formatDistanceToNow } from 'date-fns';

interface NewsWidgetProps {
  symbols?: string[];
  maxItems?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface NewsFilter {
  sentiment: 'all' | 'positive' | 'negative' | 'neutral';
  category: 'all' | 'earnings' | 'analyst' | 'merger' | 'ipo' | 'market' | 'economic';
  symbols: string[];
  timeframe: '1h' | '6h' | '24h' | '7d';
}

const NewsWidget: React.FC<NewsWidgetProps> = ({
  symbols = [],
  maxItems = 20,
  autoRefresh = true,
  refreshInterval = 60000 // 1 minute
}) => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [filteredNews, setFilteredNews] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedItem, setExpandedItem] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filter, setFilter] = useState<NewsFilter>({
    sentiment: 'all',
    category: 'all',
    symbols: symbols,
    timeframe: '24h'
  });

  const webSocket = useWebSocket({
    autoConnect: true
  });

  // Handle real-time news updates
  function handleNewsUpdate(data: any) {
    const newsItem = data as NewsItem;
    setNews(prev => [newsItem, ...prev.slice(0, maxItems - 1)]);
  }

  // Register news update handler
  useEffect(() => {
    webSocket.registerMessageHandler('news_update', handleNewsUpdate);
    
    return () => {
      webSocket.unregisterMessageHandler('news_update');
    };
  }, [webSocket]);

  // Fetch initial news data
  const fetchNews = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        limit: maxItems.toString(),
        timeframe: filter.timeframe,
        ...(filter.symbols.length > 0 && { symbols: filter.symbols.join(',') }),
        ...(filter.category !== 'all' && { category: filter.category }),
        ...(filter.sentiment !== 'all' && { sentiment: filter.sentiment })
      });

      const response = await fetch(`/api/news?${params}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch news');
      }

      const newsData: NewsItem[] = await response.json();
      
      // Mock data for demonstration
      const mockNews: NewsItem[] = [
        {
          id: 'news-1',
          title: 'Apple Reports Strong Q4 Earnings, Beats Revenue Expectations',
          summary: 'Apple Inc. reported quarterly revenue of $119.6 billion, surpassing analyst estimates of $117.8 billion. iPhone sales remained strong despite economic headwinds.',
          content: 'Apple Inc. (NASDAQ: AAPL) today announced financial results for its fiscal 2024 fourth quarter ended September 30, 2024. The company posted quarterly revenue of $119.6 billion, up 1% year over year, and quarterly earnings per diluted share of $1.60, down 3% year over year.',
          source: 'Reuters',
          publishedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
          sentiment: 'positive',
          sentimentScore: 0.75,
          symbols: ['AAPL'],
          categories: ['earnings'],
          url: 'https://example.com/apple-earnings',
          imageUrl: 'https://via.placeholder.com/300x200?text=Apple+Earnings'
        },
        {
          id: 'news-2',
          title: 'Federal Reserve Hints at Potential Rate Cut in December Meeting',
          summary: 'Fed officials signal openness to monetary policy adjustments amid cooling inflation data and labor market softening.',
          source: 'Bloomberg',
          publishedAt: new Date(Date.now() - 90 * 60 * 1000).toISOString(), // 90 minutes ago
          sentiment: 'positive',
          sentimentScore: 0.6,
          symbols: ['SPY', 'QQQ'],
          categories: ['economic'],
          url: 'https://example.com/fed-rate-cut'
        },
        {
          id: 'news-3',
          title: 'Tesla Stock Surges on Strong China Delivery Numbers',
          summary: 'Tesla reported record-breaking delivery numbers from its Shanghai Gigafactory, driving the stock up 8% in pre-market trading.',
          source: 'CNBC',
          publishedAt: new Date(Date.now() - 150 * 60 * 1000).toISOString(), // 2.5 hours ago
          sentiment: 'positive',
          sentimentScore: 0.8,
          symbols: ['TSLA'],
          categories: ['market'],
          url: 'https://example.com/tesla-china-deliveries'
        },
        {
          id: 'news-4',
          title: 'Microsoft Azure Growth Slows, Shares Drop in After-Hours Trading',
          summary: 'Microsoft reported Azure revenue growth of 29%, below analyst expectations of 32%, causing shares to decline 4% after hours.',
          source: 'MarketWatch',
          publishedAt: new Date(Date.now() - 240 * 60 * 1000).toISOString(), // 4 hours ago
          sentiment: 'negative',
          sentimentScore: -0.45,
          symbols: ['MSFT'],
          categories: ['earnings'],
          url: 'https://example.com/microsoft-azure-growth'
        },
        {
          id: 'news-5',
          title: 'NVIDIA Announces New AI Chip Partnership with Google Cloud',
          summary: 'NVIDIA and Google Cloud announce expanded partnership to accelerate AI workloads with next-generation GPU architecture.',
          source: 'TechCrunch',
          publishedAt: new Date(Date.now() - 300 * 60 * 1000).toISOString(), // 5 hours ago
          sentiment: 'positive',
          sentimentScore: 0.7,
          symbols: ['NVDA', 'GOOGL'],
          categories: ['market'],
          url: 'https://example.com/nvidia-google-partnership'
        },
        {
          id: 'news-6',
          title: 'S&P 500 Reaches New All-Time High Amid Tech Sector Rally',
          summary: 'The S&P 500 index closed at a record high of 4,847 points, driven by strong performance in technology and AI-related stocks.',
          source: 'Financial Times',
          publishedAt: new Date(Date.now() - 360 * 60 * 1000).toISOString(), // 6 hours ago
          sentiment: 'positive',
          sentimentScore: 0.65,
          symbols: ['SPY'],
          categories: ['market'],
          url: 'https://example.com/sp500-record-high'
        }
      ];

      setNews(mockNews);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load news');
    } finally {
      setIsLoading(false);
    }
  }, [maxItems, filter]);

  // Filter news based on current filter settings
  useEffect(() => {
    let filtered = [...news];

    if (filter.sentiment !== 'all') {
      filtered = filtered.filter(item => item.sentiment === filter.sentiment);
    }

    if (filter.category !== 'all') {
      filtered = filtered.filter(item => item.categories.includes(filter.category));
    }

    if (filter.symbols.length > 0) {
      filtered = filtered.filter(item => 
        item.symbols.some(symbol => filter.symbols.includes(symbol))
      );
    }

    // Filter by timeframe
    const now = new Date();
    const timeframeMins = {
      '1h': 60,
      '6h': 360,
      '24h': 1440,
      '7d': 10080
    };

    filtered = filtered.filter(item => {
      const itemTime = new Date(item.publishedAt);
      const diffMinutes = (now.getTime() - itemTime.getTime()) / (1000 * 60);
      return diffMinutes <= timeframeMins[filter.timeframe];
    });

    setFilteredNews(filtered);
  }, [news, filter]);

  // Auto refresh news
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchNews, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, fetchNews]);

  // Initial load
  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  // Subscribe to news updates via WebSocket
  useEffect(() => {
    if (webSocket.isConnected) {
      webSocket.subscribe('news');
      if (filter.symbols.length > 0) {
        filter.symbols.forEach(symbol => {
          webSocket.subscribe(`news:${symbol}`);
        });
      }
    }

    return () => {
      if (webSocket.isConnected) {
        webSocket.unsubscribe('news');
        if (filter.symbols.length > 0) {
          filter.symbols.forEach(symbol => {
            webSocket.unsubscribe(`news:${symbol}`);
          });
        }
      }
    };
  }, [webSocket.isConnected, filter.symbols, webSocket]);

  const getSentimentColor = (sentiment: string, score: number) => {
    if (sentiment === 'positive') return 'text-green-600';
    if (sentiment === 'negative') return 'text-red-600';
    return 'text-gray-600';
  };

  const getSentimentBadge = (sentiment: string, score: number) => {
    const absScore = Math.abs(score);
    if (sentiment === 'positive') {
      return (
        <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded-full">
          +{(score * 100).toFixed(0)}%
        </span>
      );
    }
    if (sentiment === 'negative') {
      return (
        <span className="px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 rounded-full">
          {(score * 100).toFixed(0)}%
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
        Neutral
      </span>
    );
  };

  const toggleExpanded = (itemId: string) => {
    setExpandedItem(expandedItem === itemId ? null : itemId);
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading financial news...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <NewspaperIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Financial News ({filteredNews.length})
            </h3>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Live indicator */}
            {webSocket.isConnected && (
              <div className="flex items-center text-xs text-green-600">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></div>
                LIVE
              </div>
            )}
            
            {/* Filter toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="p-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
            >
              <FunnelIcon className="w-4 h-4" />
            </button>
            
            {/* Refresh button */}
            <button
              onClick={fetchNews}
              disabled={isLoading}
              className="p-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white disabled:opacity-50"
            >
              <ClockIcon className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="mt-3 space-y-2"
            >
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={filter.sentiment}
                  onChange={(e) => setFilter(prev => ({ ...prev, sentiment: e.target.value as any }))}
                  className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="all">All Sentiment</option>
                  <option value="positive">Positive</option>
                  <option value="negative">Negative</option>
                  <option value="neutral">Neutral</option>
                </select>

                <select
                  value={filter.category}
                  onChange={(e) => setFilter(prev => ({ ...prev, category: e.target.value as any }))}
                  className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="all">All Categories</option>
                  <option value="earnings">Earnings</option>
                  <option value="analyst">Analyst Reports</option>
                  <option value="merger">M&A</option>
                  <option value="ipo">IPO</option>
                  <option value="market">Market News</option>
                  <option value="economic">Economic</option>
                </select>
              </div>

              <select
                value={filter.timeframe}
                onChange={(e) => setFilter(prev => ({ ...prev, timeframe: e.target.value as any }))}
                className="w-full text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="1h">Last Hour</option>
                <option value="6h">Last 6 Hours</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
              </select>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* News List */}
      <div className="flex-1 overflow-auto">
        {error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-red-600">{error}</p>
              <button
                onClick={fetchNews}
                className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Retry
              </button>
            </div>
          </div>
        ) : filteredNews.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">No news found for current filters</p>
          </div>
        ) : (
          <div className="space-y-3 p-4">
            <AnimatePresence>
              {filteredNews.map((item, index) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                  className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 hover:shadow-md transition-shadow"
                >
                  <div className="p-4">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2 cursor-pointer hover:text-blue-600"
                            onClick={() => toggleExpanded(item.id)}>
                          {item.title}
                        </h4>
                        
                        <div className="flex items-center space-x-2 mt-1">
                          <span className="text-xs text-gray-500">{item.source}</span>
                          <span className="text-xs text-gray-400">•</span>
                          <span className="text-xs text-gray-500">
                            {formatDistanceToNow(new Date(item.publishedAt), { addSuffix: true })}
                          </span>
                        </div>
                      </div>
                      
                      {getSentimentBadge(item.sentiment, item.sentimentScore)}
                    </div>

                    {/* Summary */}
                    <p className="text-sm text-gray-600 dark:text-gray-300 mb-3 line-clamp-2">
                      {item.summary}
                    </p>

                    {/* Symbols and Categories */}
                    <div className="flex items-center justify-between">
                      <div className="flex flex-wrap gap-1">
                        {item.symbols.map(symbol => (
                          <span
                            key={symbol}
                            className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded"
                          >
                            {symbol}
                          </span>
                        ))}
                        {item.categories.map(category => (
                          <span
                            key={category}
                            className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
                          >
                            {category}
                          </span>
                        ))}
                      </div>

                      <div className="flex items-center space-x-2">
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                          </a>
                        )}
                        
                        {item.content && (
                          <button
                            onClick={() => toggleExpanded(item.id)}
                            className="text-gray-600 hover:text-gray-800"
                          >
                            {expandedItem === item.id ? (
                              <ChevronUpIcon className="w-4 h-4" />
                            ) : (
                              <ChevronDownIcon className="w-4 h-4" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Expanded Content */}
                    <AnimatePresence>
                      {expandedItem === item.id && item.content && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: 0.2 }}
                          className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600"
                        >
                          <p className="text-sm text-gray-700 dark:text-gray-300">
                            {item.content}
                          </p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};

export default NewsWidget;