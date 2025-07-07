import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  MinusIcon,
  ChartBarIcon,
  CalculatorIcon,
  LightBulbIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface StrategyLeg {
  id: string;
  optionType: 'call' | 'put' | 'stock';
  side: 'long' | 'short';
  quantity: number;
  strikePrice?: number;
  premium?: number;
  expiration?: string;
}

interface StrategyTemplate {
  name: string;
  type: string;
  description: string;
  legs: Omit<StrategyLeg, 'id'>[];
  marketOutlook: string;
  complexity: 'Beginner' | 'Intermediate' | 'Advanced';
  maxProfit: string;
  maxLoss: string;
}

const strategyTemplates: StrategyTemplate[] = [
  {
    name: 'Covered Call',
    type: 'covered_call',
    description: 'Own stock and sell call options for income',
    legs: [
      { optionType: 'stock', side: 'long', quantity: 100 },
      { optionType: 'call', side: 'short', quantity: 1 }
    ],
    marketOutlook: 'Neutral to slightly bullish',
    complexity: 'Beginner',
    maxProfit: 'Call premium + (Strike - Stock price)',
    maxLoss: 'Stock decline to zero (minus call premium)'
  },
  {
    name: 'Protective Put',
    type: 'protective_put',
    description: 'Own stock and buy put options for protection',
    legs: [
      { optionType: 'stock', side: 'long', quantity: 100 },
      { optionType: 'put', side: 'long', quantity: 1 }
    ],
    marketOutlook: 'Bullish with downside protection',
    complexity: 'Beginner',
    maxProfit: 'Unlimited (stock appreciation minus put premium)',
    maxLoss: 'Stock price - Strike + Put premium'
  },
  {
    name: 'Long Straddle',
    type: 'long_straddle',
    description: 'Buy call and put with same strike and expiration',
    legs: [
      { optionType: 'call', side: 'long', quantity: 1 },
      { optionType: 'put', side: 'long', quantity: 1 }
    ],
    marketOutlook: 'High volatility expected',
    complexity: 'Intermediate',
    maxProfit: 'Unlimited',
    maxLoss: 'Total premium paid'
  },
  {
    name: 'Iron Condor',
    type: 'iron_condor',
    description: 'Sell put spread and call spread',
    legs: [
      { optionType: 'put', side: 'long', quantity: 1 },
      { optionType: 'put', side: 'short', quantity: 1 },
      { optionType: 'call', side: 'short', quantity: 1 },
      { optionType: 'call', side: 'long', quantity: 1 }
    ],
    marketOutlook: 'Low volatility (range-bound)',
    complexity: 'Advanced',
    maxProfit: 'Net premium received',
    maxLoss: 'Strike width minus net premium'
  },
  {
    name: 'Bull Call Spread',
    type: 'bull_call_spread',
    description: 'Buy lower strike call, sell higher strike call',
    legs: [
      { optionType: 'call', side: 'long', quantity: 1 },
      { optionType: 'call', side: 'short', quantity: 1 }
    ],
    marketOutlook: 'Moderately bullish',
    complexity: 'Intermediate',
    maxProfit: 'Strike difference minus net premium',
    maxLoss: 'Net premium paid'
  }
];

interface OptionsStrategyBuilderProps {
  underlyingSymbol: string;
  underlyingPrice: number;
  availableContracts: any[];
  onStrategyCreate?: (strategy: any) => void;
}

const OptionsStrategyBuilder: React.FC<OptionsStrategyBuilderProps> = ({
  underlyingSymbol,
  underlyingPrice,
  availableContracts,
  onStrategyCreate
}) => {
  const [strategyName, setStrategyName] = useState('');
  const [legs, setLegs] = useState<StrategyLeg[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<StrategyTemplate | null>(null);
  const [showPayoffDiagram, setShowPayoffDiagram] = useState(true);
  const [analysisRange, setAnalysisRange] = useState({ min: 0.8, max: 1.2 });

  // Generate unique ID for legs
  const generateLegId = () => `leg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  // Add a new leg
  const addLeg = () => {
    const newLeg: StrategyLeg = {
      id: generateLegId(),
      optionType: 'call',
      side: 'long',
      quantity: 1,
      strikePrice: underlyingPrice,
      premium: 0,
      expiration: ''
    };
    setLegs([...legs, newLeg]);
  };

  // Remove a leg
  const removeLeg = (legId: string) => {
    setLegs(legs.filter(leg => leg.id !== legId));
  };

  // Update leg
  const updateLeg = (legId: string, updates: Partial<StrategyLeg>) => {
    setLegs(legs.map(leg => 
      leg.id === legId ? { ...leg, ...updates } : leg
    ));
  };

  // Apply template
  const applyTemplate = (template: StrategyTemplate) => {
    const templateLegs: StrategyLeg[] = template.legs.map((leg, index) => ({
      ...leg,
      id: generateLegId(),
      strikePrice: leg.optionType !== 'stock' ? underlyingPrice : undefined,
      premium: 0,
      expiration: leg.optionType !== 'stock' ? '2024-03-15' : undefined
    }));
    
    setLegs(templateLegs);
    setStrategyName(template.name);
    setSelectedTemplate(template);
  };

  // Calculate payoff diagram
  const payoffData = useMemo(() => {
    if (legs.length === 0) return [];

    const minPrice = underlyingPrice * analysisRange.min;
    const maxPrice = underlyingPrice * analysisRange.max;
    const steps = 50;
    const priceStep = (maxPrice - minPrice) / steps;

    const data = [];
    
    for (let i = 0; i <= steps; i++) {
      const price = minPrice + (i * priceStep);
      let totalPayoff = 0;

      legs.forEach(leg => {
        let legPayoff = 0;
        const multiplier = leg.side === 'long' ? 1 : -1;
        const premium = leg.premium || 0;

        if (leg.optionType === 'stock') {
          // Stock payoff (assuming entry at current price)
          legPayoff = (price - underlyingPrice) * leg.quantity;
        } else if (leg.optionType === 'call' && leg.strikePrice) {
          // Call option payoff
          const intrinsic = Math.max(0, price - leg.strikePrice);
          legPayoff = multiplier * (intrinsic - premium) * leg.quantity * 100;
        } else if (leg.optionType === 'put' && leg.strikePrice) {
          // Put option payoff
          const intrinsic = Math.max(0, leg.strikePrice - price);
          legPayoff = multiplier * (intrinsic - premium) * leg.quantity * 100;
        }

        totalPayoff += legPayoff;
      });

      data.push({
        price: price,
        payoff: totalPayoff,
        breakeven: totalPayoff === 0
      });
    }

    return data;
  }, [legs, underlyingPrice, analysisRange]);

  // Calculate key metrics
  const strategyMetrics = useMemo(() => {
    if (payoffData.length === 0) return null;

    const payoffs = payoffData.map(d => d.payoff);
    const maxProfit = Math.max(...payoffs);
    const maxLoss = Math.min(...payoffs);
    
    // Find breakeven points
    const breakevenPoints = [];
    for (let i = 0; i < payoffData.length - 1; i++) {
      if ((payoffData[i].payoff <= 0 && payoffData[i + 1].payoff >= 0) ||
          (payoffData[i].payoff >= 0 && payoffData[i + 1].payoff <= 0)) {
        // Linear interpolation for more accurate breakeven
        const p1 = payoffData[i];
        const p2 = payoffData[i + 1];
        const breakevenPrice = p1.price - (p1.payoff * (p2.price - p1.price)) / (p2.payoff - p1.payoff);
        breakevenPoints.push(breakevenPrice);
      }
    }

    // Calculate net cost/credit
    const netCost = legs.reduce((total, leg) => {
      if (leg.optionType === 'stock') return total;
      const premium = leg.premium || 0;
      const multiplier = leg.side === 'long' ? 1 : -1;
      return total + (multiplier * premium * leg.quantity * 100);
    }, 0);

    return {
      maxProfit: maxProfit === Infinity ? 'Unlimited' : `$${maxProfit.toFixed(2)}`,
      maxLoss: maxLoss === -Infinity ? 'Unlimited' : `$${Math.abs(maxLoss).toFixed(2)}`,
      breakevenPoints,
      netCost,
      netCredit: -netCost
    };
  }, [payoffData, legs]);

  const getComplexityColor = (complexity: string) => {
    switch (complexity) {
      case 'Beginner': return 'text-green-600 bg-green-100';
      case 'Intermediate': return 'text-yellow-600 bg-yellow-100';
      case 'Advanced': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
          Options Strategy Builder
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Build and analyze custom options strategies for {underlyingSymbol}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Strategy Templates */}
        <div className="lg:col-span-1">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            <LightBulbIcon className="w-5 h-5 inline mr-2" />
            Strategy Templates
          </h3>
          
          <div className="space-y-3">
            {strategyTemplates.map((template) => (
              <motion.div
                key={template.type}
                whileHover={{ scale: 1.02 }}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedTemplate?.type === template.type
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
                }`}
                onClick={() => applyTemplate(template)}
              >
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-medium text-gray-900 dark:text-white">
                    {template.name}
                  </h4>
                  <span className={`px-2 py-1 text-xs rounded-full ${getComplexityColor(template.complexity)}`}>
                    {template.complexity}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  {template.description}
                </p>
                <div className="text-xs text-gray-500 dark:text-gray-500">
                  <div>Outlook: {template.marketOutlook}</div>
                  <div>Max Profit: {template.maxProfit}</div>
                  <div>Max Loss: {template.maxLoss}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Strategy Builder */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            {/* Strategy Name */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Strategy Name
              </label>
              <input
                type="text"
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
                placeholder="Enter strategy name..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700"
              />
            </div>

            {/* Legs */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-lg font-medium text-gray-900 dark:text-white">
                  Strategy Legs
                </h4>
                <button
                  onClick={addLeg}
                  className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors flex items-center"
                >
                  <PlusIcon className="w-4 h-4 mr-1" />
                  Add Leg
                </button>
              </div>

              <div className="space-y-4">
                <AnimatePresence>
                  {legs.map((leg) => (
                    <motion.div
                      key={leg.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="p-4 border border-gray-200 dark:border-gray-600 rounded-lg"
                    >
                      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                        {/* Option Type */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Type
                          </label>
                          <select
                            value={leg.optionType}
                            onChange={(e) => updateLeg(leg.id, { optionType: e.target.value as any })}
                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded"
                          >
                            <option value="call">Call</option>
                            <option value="put">Put</option>
                            <option value="stock">Stock</option>
                          </select>
                        </div>

                        {/* Side */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Side
                          </label>
                          <select
                            value={leg.side}
                            onChange={(e) => updateLeg(leg.id, { side: e.target.value as any })}
                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded"
                          >
                            <option value="long">Long</option>
                            <option value="short">Short</option>
                          </select>
                        </div>

                        {/* Quantity */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Quantity
                          </label>
                          <input
                            type="number"
                            value={leg.quantity}
                            onChange={(e) => updateLeg(leg.id, { quantity: parseInt(e.target.value) || 0 })}
                            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded"
                            min="1"
                          />
                        </div>

                        {/* Strike Price */}
                        {leg.optionType !== 'stock' && (
                          <div>
                            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                              Strike
                            </label>
                            <input
                              type="number"
                              value={leg.strikePrice || ''}
                              onChange={(e) => updateLeg(leg.id, { strikePrice: parseFloat(e.target.value) || 0 })}
                              className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded"
                              step="0.50"
                            />
                          </div>
                        )}

                        {/* Premium */}
                        {leg.optionType !== 'stock' && (
                          <div>
                            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                              Premium
                            </label>
                            <input
                              type="number"
                              value={leg.premium || ''}
                              onChange={(e) => updateLeg(leg.id, { premium: parseFloat(e.target.value) || 0 })}
                              className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded"
                              step="0.01"
                            />
                          </div>
                        )}

                        {/* Remove Button */}
                        <div className="flex items-end">
                          <button
                            onClick={() => removeLeg(leg.id)}
                            className="p-1 text-red-600 hover:text-red-800 transition-colors"
                          >
                            <MinusIcon className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>

            {/* Analysis Controls */}
            <div className="mb-6">
              <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                <CalculatorIcon className="w-5 h-5 inline mr-2" />
                Analysis
              </h4>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Analysis Range
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="number"
                      value={analysisRange.min}
                      onChange={(e) => setAnalysisRange({...analysisRange, min: parseFloat(e.target.value)})}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded"
                      step="0.1"
                      min="0.1"
                      max="2"
                    />
                    <span className="self-center text-gray-500">to</span>
                    <input
                      type="number"
                      value={analysisRange.max}
                      onChange={(e) => setAnalysisRange({...analysisRange, max: parseFloat(e.target.value)})}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded"
                      step="0.1"
                      min="0.1"
                      max="2"
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Multiplier of current price (${underlyingPrice.toFixed(2)})
                  </p>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={() => setShowPayoffDiagram(!showPayoffDiagram)}
                    className={`px-4 py-2 rounded-md transition-colors ${
                      showPayoffDiagram
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    <ChartBarIcon className="w-4 h-4 inline mr-2" />
                    Payoff Diagram
                  </button>
                </div>

                <div className="flex items-end">
                  <button
                    onClick={() => onStrategyCreate?.({
                      name: strategyName,
                      legs: legs,
                      underlyingSymbol: underlyingSymbol,
                      underlyingPrice: underlyingPrice,
                      createdAt: new Date().toISOString()
                    })}
                    disabled={legs.length === 0 || !strategyName}
                    className="w-full px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                  >
                    Create Strategy
                  </button>
                </div>
              </div>
            </div>

            {/* Strategy Metrics */}
            {strategyMetrics && (
              <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <h4 className="font-medium text-gray-900 dark:text-white mb-3">Strategy Metrics</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Max Profit:</span>
                    <div className="font-medium text-green-600">{strategyMetrics.maxProfit}</div>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Max Loss:</span>
                    <div className="font-medium text-red-600">{strategyMetrics.maxLoss}</div>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Net Cost/Credit:</span>
                    <div className={`font-medium ${strategyMetrics.netCost >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                      ${Math.abs(strategyMetrics.netCost).toFixed(2)} {strategyMetrics.netCost >= 0 ? 'Debit' : 'Credit'}
                    </div>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">Breakevens:</span>
                    <div className="font-medium">
                      {strategyMetrics.breakevenPoints.length > 0 
                        ? strategyMetrics.breakevenPoints.map(bp => `$${bp.toFixed(2)}`).join(', ')
                        : 'None'
                      }
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Payoff Diagram */}
            {showPayoffDiagram && payoffData.length > 0 && (
              <div>
                <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Payoff Diagram
                </h4>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={payoffData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="price"
                        type="number"
                        scale="linear"
                        domain={['dataMin', 'dataMax']}
                        tickFormatter={(value) => `$${value.toFixed(0)}`}
                      />
                      <YAxis tickFormatter={(value) => `$${value.toFixed(0)}`} />
                      <Tooltip 
                        formatter={(value: number) => [`$${value.toFixed(2)}`, 'P&L']}
                        labelFormatter={(value) => `Price: $${value.toFixed(2)}`}
                      />
                      <ReferenceLine y={0} stroke="#666" strokeDasharray="2 2" />
                      <ReferenceLine x={underlyingPrice} stroke="#f59e0b" strokeDasharray="2 2" />
                      <Line 
                        type="monotone" 
                        dataKey="payoff" 
                        stroke="#3b82f6" 
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default OptionsStrategyBuilder;