import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuthStore } from '@/store/authStore';
import { Portfolio } from '@/types';
import { 
  ArrowUpIcon, 
  ArrowDownIcon,
  CurrencyDollarIcon,
  TrendingUpIcon
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

interface PortfolioValueProps {
  portfolio: Portfolio;
  className?: string;
}

export const PortfolioValue: React.FC<PortfolioValueProps> = ({ portfolio, className }) => {
  const [realTimePortfolio, setRealTimePortfolio] = useState<Portfolio>(portfolio);
  const { user } = useAuthStore();
  const { 
    isConnected, 
    subscribe, 
    unsubscribe, 
    registerMessageHandler,
    unregisterMessageHandler
  } = useWebSocket();

  useEffect(() => {
    if (isConnected && user?.id) {
      // Subscribe to user's portfolio updates
      subscribe(`portfolio.${user.id}`);
    }

    // Register handler for portfolio updates
    const handlePortfolioUpdate = (data: any) => {
      setRealTimePortfolio(prev => ({
        ...prev,
        total_value: data.total_value || prev.total_value,
        day_change: data.day_change || prev.day_change,
        day_change_percent: data.day_change_percent || prev.day_change_percent,
        cash_balance: data.cash_balance || prev.cash_balance,
        equity_value: data.equity_value || prev.equity_value,
        updated_at: data.timestamp || new Date().toISOString()
      }));
    };

    registerMessageHandler('portfolio_update', handlePortfolioUpdate);

    return () => {
      if (user?.id) {
        unsubscribe(`portfolio.${user.id}`);
      }
      unregisterMessageHandler('portfolio_update');
    };
  }, [isConnected, user?.id, subscribe, unsubscribe, registerMessageHandler, unregisterMessageHandler]);

  const isPositive = realTimePortfolio.day_change >= 0;
  const changeColor = isPositive ? 'text-success-600' : 'text-danger-600';
  const bgColor = isPositive ? 'bg-success-50' : 'bg-danger-50';
  const borderColor = isPositive ? 'border-success-200' : 'border-danger-200';

  return (
    <Card className={clsx('transition-all duration-300', className, bgColor, borderColor)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CurrencyDollarIcon className="w-6 h-6 text-primary-600" />
            <h3 className="text-lg font-semibold text-gray-900">Portfolio Value</h3>
            <div className={clsx(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-success-500 animate-pulse' : 'bg-gray-400'
            )} />
          </div>
          <div className="text-sm text-gray-500">
            {isConnected ? 'Live' : 'Last Known'}
          </div>
        </div>
      </CardHeader>

      <CardBody>
        <div className="space-y-6">
          {/* Total Value */}
          <div>
            <div className="text-3xl font-bold text-gray-900 mb-2">
              ${realTimePortfolio.total_value.toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
              })}
            </div>
            <div className={clsx('flex items-center text-lg', changeColor)}>
              {isPositive ? (
                <ArrowUpIcon className="w-5 h-5 mr-1" />
              ) : (
                <ArrowDownIcon className="w-5 h-5 mr-1" />
              )}
              <span className="font-semibold">
                {isPositive ? '+' : ''}${Math.abs(realTimePortfolio.day_change).toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2
                })}
              </span>
              <span className="ml-2 text-base">
                ({isPositive ? '+' : ''}{realTimePortfolio.day_change_percent.toFixed(2)}%)
              </span>
            </div>
          </div>

          {/* Portfolio Breakdown */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white p-4 rounded-lg border">
              <div className="flex items-center space-x-2 mb-2">
                <div className="w-3 h-3 bg-primary-500 rounded-full"></div>
                <span className="text-sm text-gray-600">Equity Value</span>
              </div>
              <div className="text-xl font-bold text-gray-900">
                ${realTimePortfolio.equity_value.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2
                })}
              </div>
              <div className="text-sm text-gray-500">
                {((realTimePortfolio.equity_value / realTimePortfolio.total_value) * 100).toFixed(1)}% of total
              </div>
            </div>

            <div className="bg-white p-4 rounded-lg border">
              <div className="flex items-center space-x-2 mb-2">
                <div className="w-3 h-3 bg-success-500 rounded-full"></div>
                <span className="text-sm text-gray-600">Cash Balance</span>
              </div>
              <div className="text-xl font-bold text-gray-900">
                ${realTimePortfolio.cash_balance.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2
                })}
              </div>
              <div className="text-sm text-gray-500">
                {((realTimePortfolio.cash_balance / realTimePortfolio.total_value) * 100).toFixed(1)}% of total
              </div>
            </div>
          </div>

          {/* Total Return */}
          <div className="bg-white p-4 rounded-lg border">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <TrendingUpIcon className="w-5 h-5 text-primary-600" />
                <span className="text-sm text-gray-600">Total Return</span>
              </div>
              <div className={clsx(
                'text-sm font-medium',
                realTimePortfolio.total_return >= 0 ? 'text-success-600' : 'text-danger-600'
              )}>
                {realTimePortfolio.total_return_percent >= 0 ? '+' : ''}{realTimePortfolio.total_return_percent.toFixed(2)}%
              </div>
            </div>
            <div className={clsx(
              'text-lg font-bold',
              realTimePortfolio.total_return >= 0 ? 'text-success-600' : 'text-danger-600'
            )}>
              {realTimePortfolio.total_return >= 0 ? '+' : ''}${Math.abs(realTimePortfolio.total_return).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
              })}
            </div>
          </div>

          {/* Portfolio Composition Chart Placeholder */}
          <div className="bg-white p-4 rounded-lg border">
            <div className="text-sm text-gray-600 mb-3">Portfolio Composition</div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className="h-full bg-primary-500 float-left"
                style={{ width: `${(realTimePortfolio.equity_value / realTimePortfolio.total_value) * 100}%` }}
              />
              <div 
                className="h-full bg-success-500 float-left"
                style={{ width: `${(realTimePortfolio.cash_balance / realTimePortfolio.total_value) * 100}%` }}
              />
            </div>
            <div className="flex justify-between mt-2 text-xs text-gray-500">
              <span>Investments</span>
              <span>Cash</span>
            </div>
          </div>

          {/* Last Update */}
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>Last updated: {new Date(realTimePortfolio.updated_at).toLocaleString()}</span>
            <div className={clsx(
              'flex items-center space-x-1',
              isConnected ? 'text-success-600' : 'text-gray-400'
            )}>
              <div className={clsx(
                'w-1.5 h-1.5 rounded-full',
                isConnected ? 'bg-success-500 animate-pulse' : 'bg-gray-400'
              )} />
              <span>Real-time updates</span>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};