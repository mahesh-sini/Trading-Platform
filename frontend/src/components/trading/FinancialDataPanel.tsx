import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Stock, FinancialData } from '@/types/trading';
import { TrendingUp, TrendingDown, DollarSign, Calendar, Info, ArrowRight } from 'lucide-react';

interface FinancialDataPanelProps {
  stock: Stock;
  showPrediction?: boolean;
  className?: string;
}

interface MLPredictionData {
  signal: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL';
  confidence: number;
  expected_return: number;
  risk_score: number;
  technical_strength: number;
  reasons: string[];
  fundamental_score?: number;
}

const FinancialDataPanel: React.FC<FinancialDataPanelProps> = ({
  stock,
  showPrediction = true,
  className = ""
}) => {
  const [financialData, setFinancialData] = useState<FinancialData | null>(null);
  const [mlPrediction, setMLPrediction] = useState<MLPredictionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'ratios' | 'dividends' | 'prediction'>('overview');

  useEffect(() => {
    if (stock?.symbol) {
      fetchFinancialData();
      if (showPrediction) {
        fetchMLPrediction();
      }
    }
  }, [stock?.symbol, showPrediction]);

  const fetchFinancialData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/stocks/financial/${stock.symbol}?exchange=${stock.exchange}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setFinancialData(data.financial_data);
        }
      }
    } catch (error) {
      console.error('Error fetching financial data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMLPrediction = async () => {
    try {
      const response = await fetch(`/api/ml/prediction/${stock.symbol}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setMLPrediction(data.prediction);
        }
      }
    } catch (error) {
      console.error('Error fetching ML prediction:', error);
    }
  };

  const formatCurrency = (value: number | undefined, currency = '₹') => {
    if (value === undefined || value === null) return 'N/A';
    if (value >= 10000000) return `${currency}${(value / 10000000).toFixed(1)}Cr`;
    if (value >= 100000) return `${currency}${(value / 100000).toFixed(1)}L`;
    if (value >= 1000) return `${currency}${(value / 1000).toFixed(1)}K`;
    return `${currency}${value.toFixed(2)}`;
  };

  const formatPercentage = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const formatRatio = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return value.toFixed(2);
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'STRONG_BUY': return 'text-green-700 bg-green-100 border-green-200';
      case 'BUY': return 'text-green-600 bg-green-50 border-green-200';
      case 'HOLD': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'SELL': return 'text-red-600 bg-red-50 border-red-200';
      case 'STRONG_SELL': return 'text-red-700 bg-red-100 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getPERating = (pe: number | undefined) => {
    if (!pe) return { rating: 'N/A', color: 'text-gray-500' };
    if (pe < 15) return { rating: 'Undervalued', color: 'text-green-600' };
    if (pe < 25) return { rating: 'Fair', color: 'text-yellow-600' };
    return { rating: 'Overvalued', color: 'text-red-600' };
  };

  const getDividendRating = (yield_val: number | undefined) => {
    if (!yield_val) return { rating: 'No Dividend', color: 'text-gray-500' };
    if (yield_val > 4) return { rating: 'High Yield', color: 'text-green-600' };
    if (yield_val > 2) return { rating: 'Good Yield', color: 'text-blue-600' };
    return { rating: 'Low Yield', color: 'text-yellow-600' };
  };

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded w-full"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {stock.symbol} Financial Analysis
            </h3>
            <p className="text-sm text-gray-500 mt-1">
              {stock.name} • {stock.exchange}
              {stock.sector && ` • ${stock.sector}`}
            </p>
          </div>
          {stock.is_fo_enabled && (
            <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
              F&O
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8 px-6">
          {['overview', 'ratios', 'dividends', ...(showPrediction ? ['prediction'] : [])].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`py-3 px-1 border-b-2 font-medium text-sm capitalize ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab === 'prediction' ? 'AI Prediction' : tab}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {activeTab === 'overview' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Key Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Market Cap</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white mt-1">
                  {formatCurrency(stock.market_cap)}
                </div>
              </div>
              
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">PE Ratio</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white mt-1">
                  {formatRatio(stock.pe_ratio)}
                </div>
                <div className={`text-xs mt-1 ${getPERating(stock.pe_ratio).color}`}>
                  {getPERating(stock.pe_ratio).rating}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Dividend Yield</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white mt-1">
                  {formatPercentage(stock.dividend_yield)}
                </div>
                <div className={`text-xs mt-1 ${getDividendRating(stock.dividend_yield).color}`}>
                  {getDividendRating(stock.dividend_yield).rating}
                </div>
              </div>

              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="text-sm font-medium text-gray-500 dark:text-gray-400">Beta</div>
                <div className="text-lg font-semibold text-gray-900 dark:text-white mt-1">
                  {formatRatio(stock.beta)}
                </div>
                <div className={`text-xs mt-1 ${
                  stock.beta && stock.beta < 1 ? 'text-green-600' : 
                  stock.beta && stock.beta > 1.5 ? 'text-red-600' : 'text-gray-500'
                }`}>
                  {stock.beta ? (stock.beta < 1 ? 'Low Volatility' : stock.beta > 1.5 ? 'High Volatility' : 'Moderate') : 'N/A'}
                </div>
              </div>
            </div>

            {/* Trading Info */}
            {(stock.lot_size || stock.tick_size || stock.face_value) && (
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-3">Trading Information</h4>
                <div className="grid grid-cols-3 gap-4">
                  {stock.lot_size && (
                    <div>
                      <div className="text-xs text-blue-700 dark:text-blue-300">Lot Size</div>
                      <div className="text-sm font-medium text-blue-900 dark:text-blue-100">{stock.lot_size}</div>
                    </div>
                  )}
                  {stock.tick_size && (
                    <div>
                      <div className="text-xs text-blue-700 dark:text-blue-300">Tick Size</div>
                      <div className="text-sm font-medium text-blue-900 dark:text-blue-100">{stock.tick_size}</div>
                    </div>
                  )}
                  {stock.face_value && (
                    <div>
                      <div className="text-xs text-blue-700 dark:text-blue-300">Face Value</div>
                      <div className="text-sm font-medium text-blue-900 dark:text-blue-100">₹{stock.face_value}</div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {activeTab === 'ratios' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Valuation Ratios */}
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">Valuation Ratios</h4>
                
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Price-to-Earnings (PE)</span>
                    <span className="text-sm font-medium">{formatRatio(stock.pe_ratio)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Price-to-Book (PB)</span>
                    <span className="text-sm font-medium">{formatRatio(stock.pb_ratio)}</span>
                  </div>

                  {financialData?.debt_to_equity && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Debt-to-Equity</span>
                      <span className="text-sm font-medium">{formatRatio(financialData.debt_to_equity)}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Profitability Ratios */}
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">Profitability</h4>
                
                <div className="space-y-3">
                  {financialData?.roe && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Return on Equity (ROE)</span>
                      <span className="text-sm font-medium">{formatPercentage(financialData.roe)}</span>
                    </div>
                  )}
                  
                  {financialData?.roa && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Return on Assets (ROA)</span>
                      <span className="text-sm font-medium">{formatPercentage(financialData.roa)}</span>
                    </div>
                  )}

                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Beta (Risk)</span>
                    <span className="text-sm font-medium">{formatRatio(stock.beta)}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Growth Metrics */}
            {(financialData?.earnings_growth || financialData?.revenue_growth) && (
              <div className="mt-6 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <h4 className="text-sm font-medium text-green-900 dark:text-green-100 mb-3">Growth Metrics</h4>
                <div className="grid grid-cols-2 gap-4">
                  {financialData.earnings_growth && (
                    <div>
                      <span className="text-xs text-green-700 dark:text-green-300">Earnings Growth</span>
                      <div className="text-sm font-medium text-green-900 dark:text-green-100">
                        {formatPercentage(financialData.earnings_growth)}
                      </div>
                    </div>
                  )}
                  {financialData.revenue_growth && (
                    <div>
                      <span className="text-xs text-green-700 dark:text-green-300">Revenue Growth</span>
                      <div className="text-sm font-medium text-green-900 dark:text-green-100">
                        {formatPercentage(financialData.revenue_growth)}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {activeTab === 'dividends' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Dividend Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                <div className="flex items-center">
                  <DollarSign className="h-5 w-5 text-purple-600 mr-2" />
                  <div className="text-sm font-medium text-purple-900 dark:text-purple-100">Dividend Yield</div>
                </div>
                <div className="text-lg font-semibold text-purple-900 dark:text-purple-100 mt-1">
                  {formatPercentage(stock.dividend_yield)}
                </div>
              </div>

              {financialData?.dividend_per_share && (
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                  <div className="flex items-center">
                    <TrendingUp className="h-5 w-5 text-purple-600 mr-2" />
                    <div className="text-sm font-medium text-purple-900 dark:text-purple-100">DPS</div>
                  </div>
                  <div className="text-lg font-semibold text-purple-900 dark:text-purple-100 mt-1">
                    ₹{financialData.dividend_per_share.toFixed(2)}
                  </div>
                </div>
              )}

              {financialData?.last_dividend_date && (
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                  <div className="flex items-center">
                    <Calendar className="h-5 w-5 text-purple-600 mr-2" />
                    <div className="text-sm font-medium text-purple-900 dark:text-purple-100">Last Dividend</div>
                  </div>
                  <div className="text-lg font-semibold text-purple-900 dark:text-purple-100 mt-1">
                    {new Date(financialData.last_dividend_date).toLocaleDateString()}
                  </div>
                </div>
              )}
            </div>

            {/* Bonus & Split History */}
            <div className="space-y-4">
              {stock.bonus_ratio && (
                <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-orange-900 dark:text-orange-100 mb-2">Bonus History</h4>
                  <div className="text-sm text-orange-800 dark:text-orange-200">
                    Latest Bonus: {stock.bonus_ratio}
                  </div>
                </div>
              )}

              {stock.split_ratio && (
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">Split History</h4>
                  <div className="text-sm text-blue-800 dark:text-blue-200">
                    Latest Split: {stock.split_ratio}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {activeTab === 'prediction' && showPrediction && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {mlPrediction ? (
              <>
                {/* Prediction Summary */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-semibold text-gray-900 dark:text-white">AI Prediction</h4>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getSignalColor(mlPrediction.signal)}`}>
                      {mlPrediction.signal.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Expected Return</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {mlPrediction.expected_return > 0 ? '+' : ''}{mlPrediction.expected_return.toFixed(1)}%
                      </div>
                    </div>
                    
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Confidence</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {(mlPrediction.confidence * 100).toFixed(0)}%
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${mlPrediction.confidence * 100}%` }}
                        ></div>
                      </div>
                    </div>

                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Risk Score</div>
                      <div className="text-2xl font-bold text-gray-900 dark:text-white">
                        {(mlPrediction.risk_score * 100).toFixed(0)}%
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                        <div 
                          className={`h-2 rounded-full ${
                            mlPrediction.risk_score < 0.3 ? 'bg-green-500' : 
                            mlPrediction.risk_score < 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${mlPrediction.risk_score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Analysis Reasons */}
                <div className="bg-white dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 p-4">
                  <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Analysis Reasons</h5>
                  <div className="space-y-2">
                    {mlPrediction.reasons.map((reason, index) => (
                      <div key={index} className="flex items-center text-sm text-gray-600 dark:text-gray-300">
                        <ArrowRight className="h-4 w-4 text-blue-500 mr-2 flex-shrink-0" />
                        {reason}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Technical Strength */}
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                  <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Technical Analysis</h5>
                  <div className="space-y-3">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600 dark:text-gray-400">Technical Strength</span>
                        <span className="font-medium">{(mlPrediction.technical_strength * 100).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${mlPrediction.technical_strength * 100}%` }}
                        ></div>
                      </div>
                    </div>

                    {mlPrediction.fundamental_score && (
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600 dark:text-gray-400">Fundamental Score</span>
                          <span className="font-medium">{(mlPrediction.fundamental_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-green-600 h-2 rounded-full"
                            style={{ width: `${mlPrediction.fundamental_score * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center py-8">
                <Info className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No Prediction Available</h4>
                <p className="text-gray-600 dark:text-gray-400">
                  ML prediction is currently unavailable for this symbol.
                </p>
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default FinancialDataPanel;