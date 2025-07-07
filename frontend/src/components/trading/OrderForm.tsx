import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion, AnimatePresence } from 'framer-motion';
import { useMarketStore } from '@/store/marketStore';
import { OrderFormData, MarketQuote, Stock } from '@/types/trading';
import StockSearchInput from '@/components/ui/StockSearchInput';
import numeral from 'numeral';
import { toast } from 'react-hot-toast';

// Form validation schema
const orderSchema = z.object({
  symbol: z.string().min(1, 'Symbol is required'),
  side: z.enum(['buy', 'sell']),
  quantity: z.number().min(1, 'Quantity must be at least 1'),
  orderType: z.enum(['market', 'limit', 'stop', 'stop_limit']),
  price: z.number().optional(),
  stopPrice: z.number().optional(),
  timeInForce: z.enum(['day', 'gtc', 'ioc', 'fok']),
}).refine((data) => {
  if ((data.orderType === 'limit' || data.orderType === 'stop_limit') && !data.price) {
    return false;
  }
  if ((data.orderType === 'stop' || data.orderType === 'stop_limit') && !data.stopPrice) {
    return false;
  }
  return true;
}, {
  message: "Price and stop price are required for limit and stop orders",
  path: ["price"]
});

interface OrderFormProps {
  symbol?: string;
  onOrderSubmit: (order: OrderFormData) => void;
  className?: string;
  exchanges?: ('NSE' | 'BSE' | 'NYSE' | 'NASDAQ')[];
}

const OrderForm: React.FC<OrderFormProps> = ({
  symbol = '',
  onOrderSubmit,
  className = '',
  exchanges = ['NSE', 'BSE']
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [estimatedCost, setEstimatedCost] = useState<number>(0);
  const [availableCash, setAvailableCash] = useState<number>(50000); // Mock data
  const [currentPosition, setCurrentPosition] = useState<number>(0); // Mock data
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null);
  
  const { quotes } = useMarketStore();
  const currentQuote = quotes[symbol];

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isValid }
  } = useForm<OrderFormData>({
    resolver: zodResolver(orderSchema),
    defaultValues: {
      symbol,
      side: 'buy',
      quantity: 1,
      orderType: 'market',
      timeInForce: 'day',
    },
    mode: 'onChange'
  });

  const watchedValues = watch();
  const { side, quantity, orderType, price } = watchedValues;

  // Calculate estimated cost
  useEffect(() => {
    let estimatedPrice = 0;
    
    if (orderType === 'market') {
      estimatedPrice = side === 'buy' ? currentQuote?.ask || 0 : currentQuote?.bid || 0;
    } else if (orderType === 'limit' || orderType === 'stop_limit') {
      estimatedPrice = price || 0;
    }
    
    const cost = quantity * estimatedPrice;
    setEstimatedCost(cost);
  }, [quantity, orderType, price, side, currentQuote]);

  // Set symbol when prop changes
  useEffect(() => {
    if (symbol && symbol !== selectedStock?.symbol) {
      setValue('symbol', symbol);
      // Try to set selected stock if we have the symbol
      setSelectedStock(prev => prev?.symbol === symbol ? prev : null);
    }
  }, [symbol, setValue, selectedStock?.symbol]);

  // Handle stock selection from search
  const handleStockSelect = (stock: Stock) => {
    setSelectedStock(stock);
    setValue('symbol', stock.symbol);
  };

  // Auto-fill price for limit orders
  useEffect(() => {
    if (orderType === 'limit' && currentQuote) {
      const suggestedPrice = side === 'buy' ? currentQuote.bid : currentQuote.ask;
      setValue('price', suggestedPrice);
    }
  }, [orderType, side, currentQuote, setValue]);

  const onSubmit = async (data: OrderFormData) => {
    setIsSubmitting(true);
    
    try {
      // Validate order
      if (side === 'buy' && estimatedCost > availableCash) {
        throw new Error('Insufficient buying power');
      }
      
      if (side === 'sell' && quantity > currentPosition) {
        throw new Error('Insufficient shares to sell');
      }

      // Submit order
      await onOrderSubmit(data);
      
      toast.success(`${side.toUpperCase()} order for ${quantity} shares of ${data.symbol} submitted successfully`);
      
      // Reset form for new order
      reset({
        symbol: data.symbol,
        side: 'buy',
        quantity: 1,
        orderType: 'market',
        timeInForce: 'day',
      });
      
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to submit order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickQuantity = (qty: number) => {
    setValue('quantity', qty);
  };

  const handleMaxQuantity = () => {
    if (side === 'sell') {
      setValue('quantity', currentPosition);
    } else {
      const maxShares = Math.floor(availableCash / (currentQuote?.ask || 1));
      setValue('quantity', maxShares);
    }
  };

  const getOrderTypeDescription = (type: string) => {
    const descriptions = {
      market: 'Execute immediately at current market price',
      limit: 'Execute only at specified price or better',
      stop: 'Execute when price reaches stop price',
      stop_limit: 'Execute as limit order when stop price is reached'
    };
    return descriptions[type as keyof typeof descriptions] || '';
  };

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Place Order</h3>
        {symbol && currentQuote && (
          <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Bid:</span>
              <span className="ml-2 font-medium text-red-600">
                ${numeral(currentQuote.bid).format('0.00')}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Ask:</span>
              <span className="ml-2 font-medium text-green-600">
                ${numeral(currentQuote.ask).format('0.00')}
              </span>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="p-4 space-y-4">
        {/* Stock Search Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Stock Symbol
          </label>
          <StockSearchInput
            placeholder="Search for stocks (e.g., RELIANCE, TCS, ICICI Bank)..."
            onStockSelect={handleStockSelect}
            selectedStock={selectedStock}
            showExchange={true}
            exchanges={exchanges}
            className=""
          />
          {errors.symbol && (
            <p className="mt-1 text-sm text-red-600">{errors.symbol.message}</p>
          )}
          
          {/* Selected Stock Info */}
          {selectedStock && (
            <div className="mt-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-md">
              <div className="flex items-center justify-between text-sm">
                <div>
                  <span className="font-medium text-blue-900 dark:text-blue-100">
                    {selectedStock.symbol}
                  </span>
                  <span className="ml-2 text-blue-700 dark:text-blue-300">
                    {selectedStock.name}
                  </span>
                </div>
                <div className="text-xs text-blue-600 dark:text-blue-400">
                  {selectedStock.exchange}
                  {selectedStock.sector && ` • ${selectedStock.sector}`}
                </div>
              </div>
              {selectedStock.price && (
                <div className="mt-1 text-xs text-blue-600 dark:text-blue-400">
                  Current Price: ₹{selectedStock.price.toFixed(2)}
                  {selectedStock.change !== undefined && selectedStock.changePercent !== undefined && (
                    <span className={`ml-2 ${
                      selectedStock.change >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {selectedStock.change >= 0 ? '+' : ''}{selectedStock.change.toFixed(2)} 
                      ({selectedStock.change >= 0 ? '+' : ''}{selectedStock.changePercent.toFixed(2)}%)
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Buy/Sell Toggle */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Action
          </label>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setValue('side', 'buy')}
              className={`py-2 px-4 rounded-md font-medium transition-colors ${
                side === 'buy'
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              BUY
            </button>
            <button
              type="button"
              onClick={() => setValue('side', 'sell')}
              className={`py-2 px-4 rounded-md font-medium transition-colors ${
                side === 'sell'
                  ? 'bg-red-500 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              SELL
            </button>
          </div>
        </div>

        {/* Quantity */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Quantity
          </label>
          <div className="flex space-x-2">
            <input
              type="number"
              {...register('quantity', { valueAsNumber: true })}
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              min="1"
            />
            <button
              type="button"
              onClick={handleMaxQuantity}
              className="px-3 py-2 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors"
            >
              Max
            </button>
          </div>
          
          {/* Quick quantity buttons */}
          <div className="mt-2 flex space-x-2">
            {[10, 50, 100, 500].map((qty) => (
              <button
                key={qty}
                type="button"
                onClick={() => handleQuickQuantity(qty)}
                className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                {qty}
              </button>
            ))}
          </div>
          
          {errors.quantity && (
            <p className="mt-1 text-sm text-red-600">{errors.quantity.message}</p>
          )}
        </div>

        {/* Order Type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Order Type
          </label>
          <select
            {...register('orderType')}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="market">Market</option>
            <option value="limit">Limit</option>
            <option value="stop">Stop</option>
            <option value="stop_limit">Stop Limit</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            {getOrderTypeDescription(orderType)}
          </p>
        </div>

        {/* Conditional Price Fields */}
        <AnimatePresence>
          {(orderType === 'limit' || orderType === 'stop_limit') && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
            >
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Limit Price
              </label>
              <input
                type="number"
                step="0.01"
                {...register('price', { valueAsNumber: true })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0.00"
              />
              {errors.price && (
                <p className="mt-1 text-sm text-red-600">{errors.price.message}</p>
              )}
            </motion.div>
          )}

          {(orderType === 'stop' || orderType === 'stop_limit') && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
            >
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Stop Price
              </label>
              <input
                type="number"
                step="0.01"
                {...register('stopPrice', { valueAsNumber: true })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0.00"
              />
              {errors.stopPrice && (
                <p className="mt-1 text-sm text-red-600">{errors.stopPrice.message}</p>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Time in Force */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Time in Force
          </label>
          <select
            {...register('timeInForce')}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="day">Day</option>
            <option value="gtc">Good Till Canceled</option>
            <option value="ioc">Immediate or Cancel</option>
            <option value="fok">Fill or Kill</option>
          </select>
        </div>

        {/* Order Summary */}
        <div className="bg-gray-50 dark:bg-gray-700 rounded-md p-3 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-300">Estimated Cost:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              ${numeral(estimatedCost).format('0,0.00')}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-600 dark:text-gray-300">Available Cash:</span>
            <span className="font-medium text-gray-900 dark:text-white">
              ${numeral(availableCash).format('0,0.00')}
            </span>
          </div>
          {side === 'sell' && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-300">Current Position:</span>
              <span className="font-medium text-gray-900 dark:text-white">
                {numeral(currentPosition).format('0,0')} shares
              </span>
            </div>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!isValid || isSubmitting}
          className={`w-full py-3 px-4 rounded-md font-medium transition-colors ${
            side === 'buy'
              ? 'bg-green-500 hover:bg-green-600 text-white'
              : 'bg-red-500 hover:bg-red-600 text-white'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isSubmitting ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Submitting...
            </div>
          ) : (
            `${side.toUpperCase()} ${quantity} ${watchedValues.symbol || 'shares'}`
          )}
        </button>
      </form>
    </div>
  );
};

export default OrderForm;