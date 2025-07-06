import React, { useState, useEffect, useRef, useCallback } from 'react';
import { debounce } from 'lodash';
import { Stock } from '@/types/trading';

interface StockSearchInputProps {
  placeholder?: string;
  onStockSelect: (stock: Stock) => void;
  selectedStock?: Stock | null;
  showExchange?: boolean;
  exchanges?: ('NSE' | 'BSE' | 'NYSE' | 'NASDAQ')[];
  className?: string;
  disabled?: boolean;
  clearOnSelect?: boolean;
}

const StockSearchInput: React.FC<StockSearchInputProps> = ({
  placeholder = "Search stocks (e.g., RELIANCE, TCS, ICICI Bank)...",
  onStockSelect,
  selectedStock,
  showExchange = true,
  exchanges = ['NSE', 'BSE'],
  className = "",
  disabled = false,
  clearOnSelect = false
}) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [selectedExchange, setSelectedExchange] = useState<'ALL' | 'NSE' | 'BSE' | 'NYSE' | 'NASDAQ'>('ALL');
  
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (searchQuery: string) => {
      if (searchQuery.length < 2) {
        setSuggestions([]);
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        
        // Build API URL with comprehensive filters
        const params = new URLSearchParams({
          q: searchQuery,
          limit: '20'
        });
        
        // Add exchange filter
        if (selectedExchange !== 'ALL') {
          params.append('exchanges', selectedExchange);
        } else if (exchanges && exchanges.length > 0) {
          params.append('exchanges', exchanges.join(','));
        }
        
        // Call comprehensive stock search API
        const response = await fetch(`/api/stocks/search?${params}`);
        
        if (!response.ok) {
          throw new Error('Stock search API failed');
        }
        
        const data = await response.json();
        
        if (data.success && data.results) {
          // Transform API results to component format
          const transformedResults: Stock[] = data.results.map((item: any) => ({
            symbol: item.symbol,
            name: item.name,
            exchange: item.exchange as 'NSE' | 'BSE' | 'NYSE' | 'NASDAQ',
            sector: item.sector,
            market_cap: item.market_cap,
            description: `${item.segment}${item.sector ? ' • ' + item.sector : ''}`,
            // Additional fields from comprehensive API
            listing_date: item.listing_date,
            price: undefined, // Will be fetched separately if needed
            change: undefined,
            changePercent: undefined,
            volume: undefined,
            last_updated: undefined,
            // Financial data
            pe_ratio: item.pe_ratio,
            pb_ratio: item.pb_ratio,
            dividend_yield: item.dividend_yield,
            beta: item.beta,
            debt_to_equity: item.debt_to_equity,
            roe: item.roe,
            roa: item.roa,
            earnings_growth: item.earnings_growth,
            revenue_growth: item.revenue_growth,
            book_value: item.book_value,
            dividend_per_share: item.dividend_per_share,
            last_dividend_date: item.last_dividend_date,
            bonus_ratio: item.bonus_ratio,
            split_ratio: item.split_ratio,
            face_value: item.face_value,
            // Enhanced metadata
            is_fo_enabled: item.is_fo_enabled,
            is_etf: item.is_etf,
            is_index: item.is_index,
            lot_size: item.lot_size,
            tick_size: item.tick_size
          }));
          
          setSuggestions(transformedResults);
        } else {
          setSuggestions([]);
        }
      } catch (error) {
        console.error('Stock search error:', error);
        
        // Fallback to mock data if API fails
        const mockResults: Stock[] = [
          {
            symbol: searchQuery.toUpperCase(),
            name: `${searchQuery} Company Limited`,
            exchange: 'NSE'
          }
        ];
        setSuggestions(mockResults);
      } finally {
        setIsLoading(false);
      }
    }, 300),
    [exchanges, selectedExchange]
  );

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setHighlightedIndex(-1);
    
    if (value.length >= 2) {
      setIsOpen(true);
      debouncedSearch(value);
    } else {
      setIsOpen(false);
      setSuggestions([]);
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) => 
          prev < suggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) => 
          prev > 0 ? prev - 1 : suggestions.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && suggestions[highlightedIndex]) {
          handleStockSelect(suggestions[highlightedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setHighlightedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  // Handle stock selection
  const handleStockSelect = (stock: Stock) => {
    onStockSelect(stock);
    setIsOpen(false);
    setHighlightedIndex(-1);
    
    if (clearOnSelect) {
      setQuery('');
    } else {
      setQuery(`${stock.symbol} - ${stock.name}`);
    }
    
    inputRef.current?.blur();
  };

  // Handle exchange filter change
  const handleExchangeChange = (exchange: 'ALL' | 'NSE' | 'BSE') => {
    setSelectedExchange(exchange);
    if (query.length >= 2) {
      debouncedSearch(query);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Set initial value if selectedStock is provided
  useEffect(() => {
    if (selectedStock && !clearOnSelect) {
      setQuery(`${selectedStock.symbol} - ${selectedStock.name}`);
    }
  }, [selectedStock, clearOnSelect]);

  // Format price change display
  const formatPriceChange = (change: number, changePercent: number) => {
    const isPositive = change >= 0;
    return (
      <span className={`text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
        {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
      </span>
    );
  };

  return (
    <div className={`relative ${className}`}>
      {/* Exchange Filter */}
      {showExchange && exchanges.length > 1 && (
        <div className="flex space-x-2 mb-2">
          <button
            type="button"
            onClick={() => handleExchangeChange('ALL')}
            className={`px-3 py-1 text-sm rounded-md border ${
              selectedExchange === 'ALL'
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
            }`}
          >
            All Exchanges
          </button>
          {exchanges.map((exchange) => (
            <button
              key={exchange}
              type="button"
              onClick={() => handleExchangeChange(exchange)}
              className={`px-3 py-1 text-sm rounded-md border ${
                selectedExchange === exchange
                  ? 'bg-blue-500 text-white border-blue-500'
                  : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
              }`}
            >
              {exchange}
            </button>
          ))}
        </div>
      )}

      {/* Search Input */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (query.length >= 2 && suggestions.length > 0) {
              setIsOpen(true);
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors ${
            disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
          }`}
        />
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
          </div>
        )}
      </div>

      {/* Suggestions Dropdown */}
      {isOpen && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto"
        >
          {isLoading ? (
            <div className="px-4 py-3 text-center text-gray-500">
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                <span>Searching stocks...</span>
              </div>
            </div>
          ) : suggestions.length === 0 ? (
            <div className="px-4 py-3 text-center text-gray-500">
              {query.length < 2 ? 'Type at least 2 characters to search' : 'No stocks found'}
            </div>
          ) : (
            <div>
              {suggestions.map((stock, index) => (
                <div
                  key={`${stock.symbol}-${stock.exchange}`}
                  onClick={() => handleStockSelect(stock)}
                  className={`px-4 py-3 cursor-pointer border-b border-gray-100 last:border-b-0 hover:bg-gray-50 ${
                    index === highlightedIndex ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-gray-900">{stock.symbol}</span>
                          <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                            {stock.exchange}
                          </span>
                          {stock.is_fo_enabled && (
                            <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-600">
                              F&O
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">{stock.name}</div>
                        {stock.sector && (
                          <div className="text-xs text-gray-500 mt-1">{stock.sector}</div>
                        )}
                      </div>
                      
                      {/* Price Information */}
                      {stock.price && (
                        <div className="text-right">
                          <div className="font-semibold text-gray-900">₹{stock.price.toFixed(2)}</div>
                          {stock.change !== undefined && stock.changePercent !== undefined && (
                            <div className="mt-1">
                              {formatPriceChange(stock.change, stock.changePercent)}
                            </div>
                        )}
                      </div>
                    )}
                    
                    {/* Financial Metrics Row */}
                    {(stock.pe_ratio || stock.dividend_yield || stock.market_cap) && (
                      <div className="flex items-center justify-between text-xs text-gray-500 pt-1 border-t border-gray-100">
                        <div className="flex items-center space-x-4">
                          {stock.pe_ratio && (
                            <span>PE: {stock.pe_ratio.toFixed(1)}</span>
                          )}
                          {stock.dividend_yield && (
                            <span>Div: {stock.dividend_yield.toFixed(1)}%</span>
                          )}
                          {stock.market_cap && (
                            <span>
                              MCap: {stock.market_cap >= 10000000 
                                ? `₹${(stock.market_cap / 10000000).toFixed(1)}Cr` 
                                : stock.market_cap >= 100000 
                                ? `₹${(stock.market_cap / 100000).toFixed(1)}L` 
                                : `₹${(stock.market_cap / 1000).toFixed(1)}K`}
                            </span>
                          )}
                        </div>
                        {stock.beta && (
                          <span className={`${
                            stock.beta < 1 ? 'text-green-600' : 
                            stock.beta > 1.5 ? 'text-red-600' : 'text-gray-500'
                          }`}>
                            β: {stock.beta.toFixed(2)}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default StockSearchInput;