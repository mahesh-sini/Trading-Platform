import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import StockSearchInput from '@/components/ui/StockSearchInput';
import { Stock } from '@/types/trading';
import {
  PlusIcon,
  TrashIcon,
  EyeIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

interface WatchlistItem extends Stock {
  addedAt: string;
  alerts?: {
    upperLimit?: number;
    lowerLimit?: number;
  };
}

interface WatchlistWidgetProps {
  userId: string;
  onSymbolSelect?: (symbol: string) => void;
  selectedSymbol?: string;
  className?: string;
}

const WatchlistWidget: React.FC<WatchlistWidgetProps> = ({
  userId,
  onSymbolSelect,
  selectedSymbol,
  className = ""
}) => {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);

  // Load watchlist on component mount
  useEffect(() => {
    loadWatchlist();
  }, [userId]);

  const loadWatchlist = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`/api/watchlists?userId=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setWatchlist(data.watchlist || []);
      } else {
        console.error('Failed to load watchlist');
        // Set some default stocks for demo
        setWatchlist([
          {
            symbol: 'RELIANCE',
            name: 'Reliance Industries Limited',
            exchange: 'NSE',
            price: 2458.75,
            change: 12.50,
            changePercent: 0.51,
            volume: 1234567,
            sector: 'Oil & Gas',
            addedAt: new Date().toISOString()
          },
          {
            symbol: 'TCS',
            name: 'Tata Consultancy Services Limited',
            exchange: 'NSE',
            price: 3567.80,
            change: -15.20,
            changePercent: -0.42,
            volume: 987654,
            sector: 'Information Technology',
            addedAt: new Date().toISOString()
          },
          {
            symbol: 'HDFCBANK',
            name: 'HDFC Bank Limited',
            exchange: 'NSE',
            price: 1642.30,
            change: 8.75,
            changePercent: 0.54,
            volume: 2345678,
            sector: 'Banking',
            addedAt: new Date().toISOString()
          }
        ]);
      }
    } catch (error) {
      console.error('Error loading watchlist:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const addToWatchlist = async (stock: Stock) => {
    try {
      const watchlistItem: WatchlistItem = {
        ...stock,
        addedAt: new Date().toISOString()
      };

      const response = await fetch('/api/watchlists', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          userId,
          stock: watchlistItem
        })
      });

      if (response.ok) {
        setWatchlist(prev => [watchlistItem, ...prev]);
        setShowAddForm(false);
      } else {
        console.error('Failed to add to watchlist');
        // Add locally for demo
        setWatchlist(prev => [watchlistItem, ...prev]);
        setShowAddForm(false);
      }
    } catch (error) {
      console.error('Error adding to watchlist:', error);
    }
  };

  const removeFromWatchlist = async (symbol: string, exchange: string) => {
    try {
      const response = await fetch('/api/watchlists', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          userId,
          symbol,
          exchange
        })
      });

      if (response.ok || response.status === 404) {
        setWatchlist(prev => prev.filter(item => 
          !(item.symbol === symbol && item.exchange === exchange)
        ));
      }
    } catch (error) {
      console.error('Error removing from watchlist:', error);
      // Remove locally anyway
      setWatchlist(prev => prev.filter(item => 
        !(item.symbol === symbol && item.exchange === exchange)
      ));
    }
  };

  const formatPriceChange = (change: number, changePercent: number) => {
    const isPositive = change >= 0;
    return (
      <span className={`text-sm font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
      </span>
    );
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <Card>
        <CardHeader 
          title="My Watchlist" 
          subtitle={`${watchlist.length} stocks being monitored`}
        >
          <div className="flex justify-end">
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowAddForm(!showAddForm)}
            >
              <PlusIcon className="w-4 h-4 mr-2" />
              Add Stock
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          {/* Add Stock Form */}
          {showAddForm && (
            <div className="mb-4 p-4 bg-gray-50 rounded-lg">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Add Stock to Watchlist</h3>
              <StockSearchInput
                placeholder="Search for stocks to add..."
                onStockSelect={addToWatchlist}
                clearOnSelect={true}
                className="max-w-md"
              />
            </div>
          )}

          {/* Watchlist Items */}
          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading watchlist...</p>
            </div>
          ) : watchlist.length === 0 ? (
            <div className="text-center py-8">
              <EyeIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No stocks in your watchlist yet.</p>
              <p className="text-sm text-gray-500 mt-1">Add stocks to start monitoring their prices.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {watchlist.map((item, index) => (
                <div
                  key={`${item.symbol}-${item.exchange}`}
                  className={`p-4 border rounded-lg hover:bg-gray-50 transition-colors cursor-pointer ${
                    selectedSymbol === item.symbol ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                  }`}
                  onClick={() => onSymbolSelect?.(item.symbol)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-gray-900">{item.symbol}</span>
                        <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                          {item.exchange}
                        </span>
                        {item.sector && (
                          <span className="text-xs text-gray-500">• {item.sector}</span>
                        )}
                      </div>
                      <div className="text-sm text-gray-600 mt-1">{item.name}</div>
                    </div>
                    
                    <div className="text-right mr-4">
                      <div className="font-semibold text-gray-900">
                        ₹{item.price?.toFixed(2) || 'N/A'}
                      </div>
                      {item.change && item.changePercent && (
                        <div className="mt-1">
                          {formatPriceChange(item.change, item.changePercent)}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSymbolSelect?.(item.symbol);
                        }}
                        className="p-2 text-gray-400 hover:text-blue-600 transition-colors"
                        title="View Chart"
                      >
                        <ChartBarIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeFromWatchlist(item.symbol, item.exchange);
                        }}
                        className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                        title="Remove from Watchlist"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
};

export default WatchlistWidget;