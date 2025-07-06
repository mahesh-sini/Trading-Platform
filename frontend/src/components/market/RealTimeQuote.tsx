import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useMarketStore } from '@/store/marketStore';
import { Quote } from '@/types';
import { 
  ArrowUpIcon, 
  ArrowDownIcon,
  ChartBarIcon 
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

interface RealTimeQuoteProps {
  symbol: string;
  className?: string;
}

export const RealTimeQuote: React.FC<RealTimeQuoteProps> = ({ symbol, className }) => {
  const [isSubscribed, setIsSubscribed] = useState(false);
  const { quotes, getQuote } = useMarketStore();
  const { 
    isConnected, 
    subscribe, 
    unsubscribe, 
    connectionState,
    registerMessageHandler,
    unregisterMessageHandler
  } = useWebSocket();

  const quote = quotes[symbol];

  useEffect(() => {
    if (isConnected && !isSubscribed) {
      subscribe(`quotes.${symbol}`);
      setIsSubscribed(true);
    }

    // Register handler for quote updates
    const handleQuoteUpdate = (data: any) => {
      if (data.symbol === symbol) {
        // Quote will be automatically updated in store via useWebSocket hook
      }
    };

    registerMessageHandler('quote_update', handleQuoteUpdate);

    return () => {
      if (isSubscribed) {
        unsubscribe(`quotes.${symbol}`);
        setIsSubscribed(false);
      }
      unregisterMessageHandler('quote_update');
    };
  }, [isConnected, isSubscribed, symbol, subscribe, unsubscribe, registerMessageHandler, unregisterMessageHandler]);

  // Fetch initial quote if not available
  useEffect(() => {
    if (!quote) {
      getQuote(symbol);
    }
  }, [symbol, quote, getQuote]);

  if (!quote) {
    return (
      <Card className={className}>
        <CardBody>
          <div className="animate-pulse">
            <div className="flex items-center justify-between mb-4">
              <div className="h-6 bg-gray-200 rounded w-20"></div>
              <div className="h-4 bg-gray-200 rounded w-16"></div>
            </div>
            <div className="h-8 bg-gray-200 rounded w-32 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-24"></div>
          </div>
        </CardBody>
      </Card>
    );
  }

  const isPositive = quote.change >= 0;
  const changeColor = isPositive ? 'text-success-600' : 'text-danger-600';
  const bgColor = isPositive ? 'bg-success-50' : 'bg-danger-50';
  const borderColor = isPositive ? 'border-success-200' : 'border-danger-200';

  return (
    <Card className={clsx('transition-colors duration-200', className, bgColor, borderColor)}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-bold text-gray-900">{symbol}</h3>
            <div className={clsx(
              'w-2 h-2 rounded-full',
              isConnected ? 'bg-success-500' : 'bg-gray-400'
            )} />
          </div>
          <div className="text-sm text-gray-500">
            {connectionState === 'connected' ? 'Live' : 'Delayed'}
          </div>
        </div>
      </CardHeader>
      
      <CardBody>
        <div className="space-y-3">
          {/* Price */}
          <div>
            <div className="text-2xl font-bold text-gray-900">
              ${quote.price.toFixed(2)}
            </div>
            <div className={clsx('flex items-center text-sm', changeColor)}>
              {isPositive ? (
                <ArrowUpIcon className="w-4 h-4 mr-1" />
              ) : (
                <ArrowDownIcon className="w-4 h-4 mr-1" />
              )}
              <span className="font-medium">
                {isPositive ? '+' : ''}${quote.change.toFixed(2)}
              </span>
              <span className="ml-1">
                ({isPositive ? '+' : ''}{quote.change_percent.toFixed(2)}%)
              </span>
            </div>
          </div>

          {/* Bid/Ask */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500">Bid</div>
              <div className="font-medium">${quote.bid.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-gray-500">Ask</div>
              <div className="font-medium">${quote.ask.toFixed(2)}</div>
            </div>
          </div>

          {/* Volume */}
          <div className="text-sm">
            <div className="text-gray-500">Volume</div>
            <div className="font-medium">{quote.volume.toLocaleString()}</div>
          </div>

          {/* Market Status */}
          <div className="flex items-center justify-between text-sm">
            <div className="text-gray-500">Market</div>
            <div className={clsx(
              'px-2 py-1 rounded-full text-xs font-medium',
              quote.market_status === 'open' ? 'bg-success-100 text-success-800' : 'bg-gray-100 text-gray-800'
            )}>
              {quote.market_status.replace('_', ' ').toUpperCase()}
            </div>
          </div>

          {/* Last Update */}
          <div className="text-xs text-gray-400">
            Last update: {new Date(quote.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </CardBody>
    </Card>
  );
};