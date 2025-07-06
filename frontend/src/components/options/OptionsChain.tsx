import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChartBarIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  InformationCircleIcon,
  CalendarIcon,
  CurrencyDollarIcon,
  BeakerIcon
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';

interface OptionsContract {
  id: string;
  symbol: string;
  underlying_symbol: string;
  option_type: 'call' | 'put';
  strike_price: number;
  expiration_date: string;
  last_price?: number;
  bid?: number;
  ask?: number;
  volume: number;
  open_interest: number;
  delta?: number;
  gamma?: number;
  theta?: number;
  vega?: number;
  rho?: number;
  implied_volatility?: number;
  theoretical_price?: number;
  intrinsic_value?: number;
  time_value?: number;
}

interface OptionsChainProps {
  underlyingSymbol: string;
  underlyingPrice: number;
  contracts: OptionsContract[];
  onContractSelect?: (contract: OptionsContract) => void;
  onTrade?: (contract: OptionsContract, action: 'buy' | 'sell') => void;
}

const OptionsChain: React.FC<OptionsChainProps> = ({
  underlyingSymbol,
  underlyingPrice,
  contracts,
  onContractSelect,
  onTrade
}) => {
  const [selectedExpiration, setSelectedExpiration] = useState<string>('');
  const [showGreeks, setShowGreeks] = useState(false);
  const [selectedContract, setSelectedContract] = useState<OptionsContract | null>(null);
  const [sortBy, setSortBy] = useState<'strike' | 'volume' | 'oi' | 'iv'>('strike');

  // Get unique expiration dates
  const expirationDates = useMemo(() => {
    const dates = Array.from(new Set(contracts.map(c => c.expiration_date)))
      .sort((a, b) => new Date(a).getTime() - new Date(b).getTime());
    return dates;
  }, [contracts]);

  // Set default expiration to the nearest one
  useEffect(() => {
    if (expirationDates.length > 0 && !selectedExpiration) {
      setSelectedExpiration(expirationDates[0]);
    }
  }, [expirationDates, selectedExpiration]);

  // Filter and organize contracts
  const { calls, puts } = useMemo(() => {
    const filtered = contracts.filter(c => c.expiration_date === selectedExpiration);
    
    const calls = filtered
      .filter(c => c.option_type === 'call')
      .sort((a, b) => {
        switch (sortBy) {
          case 'volume':
            return b.volume - a.volume;
          case 'oi':
            return b.open_interest - a.open_interest;
          case 'iv':
            return (b.implied_volatility || 0) - (a.implied_volatility || 0);
          default:
            return a.strike_price - b.strike_price;
        }
      });

    const puts = filtered
      .filter(c => c.option_type === 'put')
      .sort((a, b) => {
        switch (sortBy) {
          case 'volume':
            return b.volume - a.volume;
          case 'oi':
            return b.open_interest - a.open_interest;
          case 'iv':
            return (b.implied_volatility || 0) - (a.implied_volatility || 0);
          default:
            return a.strike_price - b.strike_price;
        }
      });

    return { calls, puts };
  }, [contracts, selectedExpiration, sortBy]);

  // Get strikes that have both calls and puts
  const combinedStrikes = useMemo(() => {
    const callStrikes = new Set(calls.map(c => c.strike_price));
    const putStrikes = new Set(puts.map(c => c.strike_price));
    
    const allStrikes = Array.from(new Set([...callStrikes, ...putStrikes]))
      .sort((a, b) => a - b);

    return allStrikes.map(strike => {
      const call = calls.find(c => c.strike_price === strike);
      const put = puts.find(c => c.strike_price === strike);
      return { strike, call, put };
    });
  }, [calls, puts]);

  const getMoneyness = (strike: number) => {
    const moneyness = underlyingPrice / strike;
    if (moneyness > 1.02) return 'itm'; // In the money
    if (moneyness < 0.98) return 'otm'; // Out of the money
    return 'atm'; // At the money
  };

  const formatPrice = (price?: number) => {
    if (price === undefined || price === null) return '--';
    return price.toFixed(2);
  };

  const formatPercent = (value?: number) => {
    if (value === undefined || value === null) return '--';
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatGreek = (value?: number) => {
    if (value === undefined || value === null) return '--';
    return value.toFixed(3);
  };

  const getRowColor = (moneyness: string, type: 'call' | 'put') => {
    if (moneyness === 'atm') return 'bg-yellow-50 dark:bg-yellow-900/20';
    if (moneyness === 'itm') {
      return type === 'call' 
        ? 'bg-green-50 dark:bg-green-900/20' 
        : 'bg-red-50 dark:bg-red-900/20';
    }
    return '';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Options Chain - {underlyingSymbol}
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Current Price: <span className="font-semibold">${underlyingPrice.toFixed(2)}</span>
          </p>
        </div>

        <div className="flex items-center space-x-4">
          {/* Greeks Toggle */}
          <button
            onClick={() => setShowGreeks(!showGreeks)}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              showGreeks
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            <BeakerIcon className="w-4 h-4 inline mr-1" />
            Greeks
          </button>

          {/* Sort Options */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="text-sm border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700"
          >
            <option value="strike">Sort by Strike</option>
            <option value="volume">Sort by Volume</option>
            <option value="oi">Sort by Open Interest</option>
            <option value="iv">Sort by IV</option>
          </select>
        </div>
      </div>

      {/* Expiration Selector */}
      <div className="flex flex-wrap gap-2">
        {expirationDates.map((date) => (
          <button
            key={date}
            onClick={() => setSelectedExpiration(date)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              selectedExpiration === date
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            <CalendarIcon className="w-4 h-4 inline mr-1" />
            {format(new Date(date), 'MMM dd')}
          </button>
        ))}
      </div>

      {/* Options Chain Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                {/* Calls Header */}
                <th colSpan={showGreeks ? 9 : 5} className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider bg-green-50 dark:bg-green-900/30">
                  CALLS
                </th>
                
                {/* Strike */}
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  Strike
                </th>
                
                {/* Puts Header */}
                <th colSpan={showGreeks ? 9 : 5} className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider bg-red-50 dark:bg-red-900/30">
                  PUTS
                </th>
              </tr>
              
              <tr>
                {/* Calls Columns */}
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Bid</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Ask</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Last</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Vol</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">OI</th>
                
                {showGreeks && (
                  <>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Delta</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Gamma</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Theta</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">IV</th>
                  </>
                )}
                
                {/* Strike Column */}
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Price</th>
                
                {/* Puts Columns */}
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Bid</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Ask</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Last</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Vol</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">OI</th>
                
                {showGreeks && (
                  <>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Delta</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Gamma</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Theta</th>
                    <th className="px-3 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">IV</th>
                  </>
                )}
              </tr>
            </thead>
            
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              <AnimatePresence>
                {combinedStrikes.map(({ strike, call, put }) => {
                  const moneyness = getMoneyness(strike);
                  
                  return (
                    <motion.tr
                      key={strike}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${getRowColor(moneyness, 'call')}`}
                    >
                      {/* Call Data */}
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {call ? (
                          <button
                            onClick={() => onTrade?.(call, 'buy')}
                            className="text-green-600 hover:text-green-800 font-medium"
                          >
                            {formatPrice(call.bid)}
                          </button>
                        ) : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {call ? (
                          <button
                            onClick={() => onTrade?.(call, 'sell')}
                            className="text-red-600 hover:text-red-800 font-medium"
                          >
                            {formatPrice(call.ask)}
                          </button>
                        ) : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {call ? formatPrice(call.last_price) : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {call ? call.volume.toLocaleString() : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {call ? call.open_interest.toLocaleString() : '--'}
                      </td>
                      
                      {showGreeks && (
                        <>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {call ? formatGreek(call.delta) : '--'}
                          </td>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {call ? formatGreek(call.gamma) : '--'}
                          </td>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {call ? formatGreek(call.theta) : '--'}
                          </td>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {call ? formatPercent(call.implied_volatility) : '--'}
                          </td>
                        </>
                      )}
                      
                      {/* Strike Price */}
                      <td className="px-6 py-4 whitespace-nowrap text-center">
                        <div className={`font-bold text-lg ${
                          moneyness === 'atm' ? 'text-yellow-600 dark:text-yellow-400' :
                          moneyness === 'itm' ? 'text-green-600 dark:text-green-400' :
                          'text-gray-900 dark:text-white'
                        }`}>
                          ${strike}
                        </div>
                        {moneyness === 'atm' && (
                          <div className="text-xs text-yellow-600 dark:text-yellow-400">ATM</div>
                        )}
                      </td>
                      
                      {/* Put Data */}
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {put ? (
                          <button
                            onClick={() => onTrade?.(put, 'buy')}
                            className="text-green-600 hover:text-green-800 font-medium"
                          >
                            {formatPrice(put.bid)}
                          </button>
                        ) : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {put ? (
                          <button
                            onClick={() => onTrade?.(put, 'sell')}
                            className="text-red-600 hover:text-red-800 font-medium"
                          >
                            {formatPrice(put.ask)}
                          </button>
                        ) : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {put ? formatPrice(put.last_price) : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {put ? put.volume.toLocaleString() : '--'}
                      </td>
                      <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {put ? put.open_interest.toLocaleString() : '--'}
                      </td>
                      
                      {showGreeks && (
                        <>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {put ? formatGreek(put.delta) : '--'}
                          </td>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {put ? formatGreek(put.gamma) : '--'}
                          </td>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {put ? formatGreek(put.theta) : '--'}
                          </td>
                          <td className="px-3 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            {put ? formatPercent(put.implied_volatility) : '--'}
                          </td>
                        </>
                      )}
                    </motion.tr>
                  );
                })}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      </div>

      {/* Chain Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
          <h3 className="text-lg font-semibold text-green-800 dark:text-green-300 mb-2">
            Call Summary
          </h3>
          <div className="space-y-1 text-sm">
            <div>Total Volume: {calls.reduce((sum, c) => sum + c.volume, 0).toLocaleString()}</div>
            <div>Total OI: {calls.reduce((sum, c) => sum + c.open_interest, 0).toLocaleString()}</div>
            <div>Avg IV: {formatPercent(calls.reduce((sum, c) => sum + (c.implied_volatility || 0), 0) / calls.length)}</div>
          </div>
        </div>

        <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
          <h3 className="text-lg font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
            Market Stats
          </h3>
          <div className="space-y-1 text-sm">
            <div>Put/Call Ratio: {((puts.reduce((sum, p) => sum + p.volume, 0)) / (calls.reduce((sum, c) => sum + c.volume, 0) || 1)).toFixed(2)}</div>
            <div>Total Contracts: {contracts.length}</div>
            <div>Expiration: {format(new Date(selectedExpiration), 'MMM dd, yyyy')}</div>
          </div>
        </div>

        <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-300 mb-2">
            Put Summary
          </h3>
          <div className="space-y-1 text-sm">
            <div>Total Volume: {puts.reduce((sum, p) => sum + p.volume, 0).toLocaleString()}</div>
            <div>Total OI: {puts.reduce((sum, p) => sum + p.open_interest, 0).toLocaleString()}</div>
            <div>Avg IV: {formatPercent(puts.reduce((sum, p) => sum + (p.implied_volatility || 0), 0) / puts.length)}</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OptionsChain;