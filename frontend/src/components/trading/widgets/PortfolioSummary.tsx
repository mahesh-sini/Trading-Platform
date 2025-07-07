import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Portfolio, PerformanceMetrics } from '@/types/trading';
import numeral from 'numeral';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';

interface PortfolioSummaryProps {
  userId: string;
}

interface PerformanceData {
  date: string;
  value: number;
}

const PortfolioSummary: React.FC<PortfolioSummaryProps> = ({ userId }) => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<'1D' | '1W' | '1M' | '3M' | '1Y'>('1D');
  const [isLoading, setIsLoading] = useState(true);

  // Mock data - replace with actual API calls
  useEffect(() => {
    const fetchPortfolioData = async () => {
      setIsLoading(true);
      
      // Simulate API call
      setTimeout(() => {
        const mockPortfolio: Portfolio = {
          id: 'portfolio-1',
          userId,
          totalValue: 127850.75,
          cash: 15420.50,
          equity: 112430.25,
          dayChange: 1247.32,
          dayChangePercent: 0.98,
          positions: [],
          performance: {
            totalReturn: 27850.75,
            totalReturnPercent: 27.85,
            annualizedReturn: 15.2,
            sharpeRatio: 1.45,
            maxDrawdown: -8.5,
            winRate: 68.5,
            avgWin: 2.1,
            avgLoss: -1.2,
            profitFactor: 1.8,
            calmarRatio: 1.79,
            sortinoRatio: 2.1
          },
          updatedAt: new Date().toISOString()
        };

        const mockPerformanceData: PerformanceData[] = [
          { date: '09:30', value: 126500 },
          { date: '10:00', value: 126750 },
          { date: '10:30', value: 127100 },
          { date: '11:00', value: 126900 },
          { date: '11:30', value: 127300 },
          { date: '12:00', value: 127450 },
          { date: '12:30', value: 127200 },
          { date: '13:00', value: 127600 },
          { date: '13:30', value: 127850 },
        ];

        setPortfolio(mockPortfolio);
        setPerformanceData(mockPerformanceData);
        setIsLoading(false);
      }, 1000);
    };

    fetchPortfolioData();
  }, [userId, selectedPeriod]);

  if (isLoading) {
    return (
      <div className="p-6 h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!portfolio) {
    return (
      <div className="p-6 h-full flex items-center justify-center">
        <p className="text-gray-500">Failed to load portfolio data</p>
      </div>
    );
  }

  const isPositiveChange = portfolio.dayChange >= 0;

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Portfolio Summary
          </h3>
          
          {/* Period Selector */}
          <div className="flex space-x-1">
            {(['1D', '1W', '1M', '3M', '1Y'] as const).map((period) => (
              <button
                key={period}
                onClick={() => setSelectedPeriod(period)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  selectedPeriod === period
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {period}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-4 space-y-4">
        {/* Total Value */}
        <div className="text-center">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.2 }}
          >
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              ${numeral(portfolio.totalValue).format('0,0.00')}
            </p>
            <div className={`flex items-center justify-center mt-1 ${
              isPositiveChange ? 'text-green-600' : 'text-red-600'
            }`}>
              {isPositiveChange ? (
                <ArrowUpIcon className="w-4 h-4 mr-1" />
              ) : (
                <ArrowDownIcon className="w-4 h-4 mr-1" />
              )}
              <span className="text-sm font-medium">
                ${numeral(Math.abs(portfolio.dayChange)).format('0,0.00')} 
                ({isPositiveChange ? '+' : ''}{numeral(portfolio.dayChangePercent).format('0.00')}%)
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-1">Today&apos;s Change</p>
          </motion.div>
        </div>

        {/* Performance Chart */}
        <div className="h-20">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={performanceData}>
              <Line
                type="monotone"
                dataKey="value"
                stroke={isPositiveChange ? "#10b981" : "#ef4444"}
                strokeWidth={2}
                dot={false}
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (active && payload && payload.length) {
                    return (
                      <div className="bg-white dark:bg-gray-800 p-2 border border-gray-200 dark:border-gray-600 rounded shadow-lg">
                        <p className="text-xs text-gray-600 dark:text-gray-300">{label}</p>
                        <p className="text-sm font-medium">
                          ${numeral(payload[0].value).format('0,0.00')}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Portfolio Breakdown */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              ${numeral(portfolio.equity).format('0,0')}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-300">Equity</p>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              ${numeral(portfolio.cash).format('0,0')}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-300">Cash</p>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-300">Total Return</span>
            <div className="text-right">
              <span className={`text-sm font-medium ${
                portfolio.performance.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {portfolio.performance.totalReturn >= 0 ? '+' : ''}
                ${numeral(portfolio.performance.totalReturn).format('0,0.00')}
              </span>
              <div className={`text-xs ${
                portfolio.performance.totalReturnPercent >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ({portfolio.performance.totalReturnPercent >= 0 ? '+' : ''}
                {numeral(portfolio.performance.totalReturnPercent).format('0.00')}%)
              </div>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-300">Annualized Return</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {numeral(portfolio.performance.annualizedReturn).format('0.0')}%
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-300">Sharpe Ratio</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {numeral(portfolio.performance.sharpeRatio).format('0.00')}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-300">Max Drawdown</span>
            <span className="text-sm font-medium text-red-600">
              {numeral(portfolio.performance.maxDrawdown).format('0.0')}%
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-300">Win Rate</span>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {numeral(portfolio.performance.winRate).format('0.0')}%
            </span>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-2 mt-4">
          <button className="px-3 py-2 bg-green-500 text-white rounded-md text-sm font-medium hover:bg-green-600 transition-colors">
            Buy
          </button>
          <button className="px-3 py-2 bg-red-500 text-white rounded-md text-sm font-medium hover:bg-red-600 transition-colors">
            Sell
          </button>
        </div>
      </div>
    </div>
  );
};

export default PortfolioSummary;