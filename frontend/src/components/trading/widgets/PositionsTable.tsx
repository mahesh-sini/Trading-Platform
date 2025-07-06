import React, { useState, useEffect, useMemo } from 'react';
import { Position } from '@/types/trading';
import numeral from 'numeral';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';
import { motion, AnimatePresence } from 'framer-motion';

interface PositionsTableProps {
  userId: string;
  onSymbolSelect?: (symbol: string) => void;
}

const PositionsTable: React.FC<PositionsTableProps> = ({ userId, onSymbolSelect }) => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [sortBy, setSortBy] = useState<keyof Position>('marketValue');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const fetchPositions = async () => {
      setIsLoading(true);
      
      // Simulate API call
      setTimeout(() => {
        const mockPositions: Position[] = [
          {
            id: 'pos-1',
            symbol: 'AAPL',
            quantity: 100,
            averagePrice: 155.25,
            currentPrice: 162.45,
            marketValue: 16245.00,
            unrealizedPnl: 720.00,
            unrealizedPnlPercent: 4.64,
            realizedPnl: 0,
            dayChange: 125.50,
            dayChangePercent: 0.78,
            openDate: '2024-01-15T09:30:00Z',
            sector: 'Technology',
            industry: 'Consumer Electronics'
          },
          {
            id: 'pos-2',
            symbol: 'TSLA',
            quantity: 50,
            averagePrice: 245.80,
            currentPrice: 238.90,
            marketValue: 11945.00,
            unrealizedPnl: -345.00,
            unrealizedPnlPercent: -2.81,
            realizedPnl: 0,
            dayChange: -89.50,
            dayChangePercent: -0.74,
            openDate: '2024-01-10T10:15:00Z',
            sector: 'Technology',
            industry: 'Auto Manufacturers'
          },
          {
            id: 'pos-3',
            symbol: 'MSFT',
            quantity: 75,
            averagePrice: 285.50,
            currentPrice: 298.25,
            marketValue: 22368.75,
            unrealizedPnl: 956.25,
            unrealizedPnlPercent: 4.47,
            realizedPnl: 0,
            dayChange: 234.75,
            dayChangePercent: 1.06,
            openDate: '2024-01-08T11:20:00Z',
            sector: 'Technology',
            industry: 'Software'
          },
          {
            id: 'pos-4',
            symbol: 'NVDA',
            quantity: 25,
            averagePrice: 425.30,
            currentPrice: 445.75,
            marketValue: 11143.75,
            unrealizedPnl: 511.25,
            unrealizedPnlPercent: 4.81,
            realizedPnl: 0,
            dayChange: 178.25,
            dayChangePercent: 1.62,
            openDate: '2024-01-12T14:45:00Z',
            sector: 'Technology',
            industry: 'Semiconductors'
          },
          {
            id: 'pos-5',
            symbol: 'SPY',
            quantity: 200,
            averagePrice: 425.80,
            currentPrice: 432.15,
            marketValue: 86430.00,
            unrealizedPnl: 1270.00,
            unrealizedPnlPercent: 1.49,
            realizedPnl: 0,
            dayChange: 356.00,
            dayChangePercent: 0.41,
            openDate: '2024-01-05T09:30:00Z',
            sector: 'ETF',
            industry: 'ETF'
          }
        ];

        setPositions(mockPositions);
        setIsLoading(false);
      }, 1000);
    };

    fetchPositions();
  }, [userId]);

  // Sort positions
  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      const aValue = a[sortBy];
      const bValue = b[sortBy];
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortOrder === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortOrder === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      return 0;
    });
  }, [positions, sortBy, sortOrder]);

  const handleSort = (column: keyof Position) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const handlePositionClick = (position: Position) => {
    setSelectedPosition(selectedPosition === position.id ? null : position.id);
    onSymbolSelect?.(position.symbol);
  };

  const getTotalValue = () => {
    return positions.reduce((sum, pos) => sum + pos.marketValue, 0);
  };

  const getTotalPnL = () => {
    return positions.reduce((sum, pos) => sum + pos.unrealizedPnl, 0);
  };

  const getTotalDayChange = () => {
    return positions.reduce((sum, pos) => sum + pos.dayChange, 0);
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Positions ({positions.length})
          </h3>
          
          {/* Summary Stats */}
          <div className="flex space-x-4 text-sm">
            <div className="text-center">
              <p className="font-medium text-gray-900 dark:text-white">
                ${numeral(getTotalValue()).format('0,0')}
              </p>
              <p className="text-xs text-gray-500">Total Value</p>
            </div>
            <div className="text-center">
              <p className={`font-medium ${
                getTotalPnL() >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {getTotalPnL() >= 0 ? '+' : ''}${numeral(getTotalPnL()).format('0,0')}
              </p>
              <p className="text-xs text-gray-500">Unrealized P&L</p>
            </div>
            <div className="text-center">
              <p className={`font-medium ${
                getTotalDayChange() >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {getTotalDayChange() >= 0 ? '+' : ''}${numeral(getTotalDayChange()).format('0,0')}
              </p>
              <p className="text-xs text-gray-500">Today</p>
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {positions.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">No positions found</p>
          </div>
        ) : (
          <div className="min-w-full">
            {/* Table Header */}
            <div className="grid grid-cols-8 gap-2 p-3 bg-gray-50 dark:bg-gray-700 text-xs font-medium text-gray-600 dark:text-gray-300 uppercase tracking-wider border-b border-gray-200 dark:border-gray-600">
              <button
                onClick={() => handleSort('symbol')}
                className="text-left hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Symbol {sortBy === 'symbol' && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
              <button
                onClick={() => handleSort('quantity')}
                className="text-right hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Qty {sortBy === 'quantity' && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
              <button
                onClick={() => handleSort('averagePrice')}
                className="text-right hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Avg Price {sortBy === 'averagePrice' && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
              <button
                onClick={() => handleSort('currentPrice')}
                className="text-right hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Last Price {sortBy === 'currentPrice' && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
              <button
                onClick={() => handleSort('marketValue')}
                className="text-right hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Market Value {sortBy === 'marketValue' && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
              <button
                onClick={() => handleSort('unrealizedPnl')}
                className="text-right hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Unrealized P&L {sortBy === 'unrealizedPnl' && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
              <button
                onClick={() => handleSort('dayChange')}
                className="text-right hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Day Change {sortBy === 'dayChange' && (sortOrder === 'asc' ? '↑' : '↓')}
              </button>
              <div className="text-center">Actions</div>
            </div>

            {/* Table Body */}
            <AnimatePresence>
              {sortedPositions.map((position, index) => (
                <motion.div
                  key={position.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                  className={`grid grid-cols-8 gap-2 p-3 border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors cursor-pointer ${
                    selectedPosition === position.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}
                  onClick={() => handlePositionClick(position)}
                >
                  {/* Symbol */}
                  <div className="flex items-center">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {position.symbol}
                      </p>
                      <p className="text-xs text-gray-500">{position.sector}</p>
                    </div>
                  </div>

                  {/* Quantity */}
                  <div className="text-right text-sm text-gray-900 dark:text-white">
                    {numeral(position.quantity).format('0,0')}
                  </div>

                  {/* Average Price */}
                  <div className="text-right text-sm text-gray-900 dark:text-white">
                    ${numeral(position.averagePrice).format('0.00')}
                  </div>

                  {/* Current Price */}
                  <div className="text-right text-sm text-gray-900 dark:text-white">
                    ${numeral(position.currentPrice).format('0.00')}
                  </div>

                  {/* Market Value */}
                  <div className="text-right text-sm font-medium text-gray-900 dark:text-white">
                    ${numeral(position.marketValue).format('0,0')}
                  </div>

                  {/* Unrealized P&L */}
                  <div className="text-right">
                    <div className={`text-sm font-medium ${
                      position.unrealizedPnl >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {position.unrealizedPnl >= 0 ? '+' : ''}${numeral(position.unrealizedPnl).format('0,0')}
                    </div>
                    <div className={`text-xs ${
                      position.unrealizedPnlPercent >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      ({position.unrealizedPnlPercent >= 0 ? '+' : ''}{numeral(position.unrealizedPnlPercent).format('0.00')}%)
                    </div>
                  </div>

                  {/* Day Change */}
                  <div className="text-right">
                    <div className={`flex items-center justify-end text-sm font-medium ${
                      position.dayChange >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {position.dayChange >= 0 ? (
                        <ArrowUpIcon className="w-3 h-3 mr-1" />
                      ) : (
                        <ArrowDownIcon className="w-3 h-3 mr-1" />
                      )}
                      {position.dayChange >= 0 ? '+' : ''}${numeral(position.dayChange).format('0,0')}
                    </div>
                    <div className={`text-xs ${
                      position.dayChangePercent >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      ({position.dayChangePercent >= 0 ? '+' : ''}{numeral(position.dayChangePercent).format('0.00')}%)
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-center space-x-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle buy action
                      }}
                      className="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
                    >
                      Buy
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle sell action
                      }}
                      className="px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                    >
                      Sell
                    </button>
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

export default PositionsTable;