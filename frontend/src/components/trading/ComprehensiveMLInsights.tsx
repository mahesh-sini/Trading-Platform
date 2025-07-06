import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

interface SymbolPrediction {
  rank: number;
  symbol: string;
  name: string;
  exchange: string;
  segment: string;
  sector: string;
  signal: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL';
  confidence: number;
  expected_return: number;
  risk_score: number;
  technical_strength: number;
  reasons: string[];
  score: number;
}

interface TopPicksResponse {
  success: boolean;
  top_picks: SymbolPrediction[];
  analysis: {
    segment: string;
    total_symbols_analyzed: number;
    market_sentiment: string;
    top_sectors: string[];
    generated_at: string;
  };
}

interface SectorAnalysis {
  sector: string;
  metrics: {
    symbol_count: number;
    avg_expected_return: number;
    avg_confidence: number;
    bullish_percentage: number;
  };
  top_pick: {
    symbol: string;
    name: string;
    exchange: string;
    signal: string;
    expected_return: number;
    confidence: number;
  };
}

const ComprehensiveMLInsights: React.FC = () => {
  const [topPicks, setTopPicks] = useState<SymbolPrediction[]>([]);
  const [sectorAnalysis, setSectorAnalysis] = useState<SectorAnalysis[]>([]);
  const [marketOverview, setMarketOverview] = useState<any>(null);
  const [selectedSegment, setSelectedSegment] = useState<string>('ALL');
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const segments = [
    { value: 'ALL', label: 'All Segments', icon: '🎯' },
    { value: 'EQUITY', label: 'Equity Stocks', icon: '📈' },
    { value: 'COMMODITY', label: 'Commodities', icon: '🥇' },
    { value: 'CURRENCY', label: 'Currency', icon: '💱' },
    { value: 'INDEX', label: 'Indices', icon: '📊' },
    { value: 'ETF', label: 'ETFs', icon: '🏛️' }
  ];

  useEffect(() => {
    fetchMLInsights();
    const interval = setInterval(fetchMLInsights, 300000); // Update every 5 minutes
    return () => clearInterval(interval);
  }, [selectedSegment]);

  const fetchMLInsights = async () => {
    try {
      setLoading(true);

      // Fetch top picks
      const segment = selectedSegment === 'ALL' ? '' : selectedSegment;
      const topPicksResponse = await fetch(`/api/ml/top-picks?segment=${segment}&limit=15`);
      const topPicksData: TopPicksResponse = await topPicksResponse.json();
      
      if (topPicksData.success) {
        setTopPicks(topPicksData.top_picks);
        setLastUpdate(new Date().toLocaleTimeString());
      }

      // Fetch sector analysis
      const sectorResponse = await fetch('/api/ml/sector-analysis');
      const sectorData = await sectorResponse.json();
      
      if (sectorData.success) {
        setSectorAnalysis(sectorData.sector_analysis);
      }

      // Fetch market overview
      const overviewResponse = await fetch('/api/ml/market-overview');
      const overviewData = await overviewResponse.json();
      
      if (overviewData.success) {
        setMarketOverview(overviewData.market_overview);
      }

    } catch (error) {
      console.error('Error fetching ML insights:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'STRONG_BUY': return 'text-green-700 bg-green-100';
      case 'BUY': return 'text-green-600 bg-green-50';
      case 'HOLD': return 'text-yellow-600 bg-yellow-50';
      case 'SELL': return 'text-red-600 bg-red-50';
      case 'STRONG_SELL': return 'text-red-700 bg-red-100';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'Bullish': return 'text-green-700 bg-green-100';
      case 'Bearish': return 'text-red-700 bg-red-100';
      case 'Neutral': return 'text-yellow-700 bg-yellow-100';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  if (loading && topPicks.length === 0) {
    return (
      <div className="space-y-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
            <span className="text-gray-600">Analyzing 107 symbols across all markets...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              🤖 AI Trading Insights
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-1">
              ML-powered analysis across NSE, BSE, MCX • 107 symbols • Real-time predictions
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Last updated: {lastUpdate}</div>
            {marketOverview && (
              <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getSentimentColor(marketOverview.overall_sentiment)}`}>
                Market: {marketOverview.overall_sentiment}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Segment Filter */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex flex-wrap gap-2">
          {segments.map((segment) => (
            <button
              key={segment.value}
              onClick={() => setSelectedSegment(segment.value)}
              className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedSegment === segment.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <span className="mr-2">{segment.icon}</span>
              {segment.label}
            </button>
          ))}
        </div>
      </div>

      {/* Market Overview Cards */}
      {marketOverview && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{marketOverview.total_symbols_tracked}</div>
              <div className="text-sm text-gray-600">Symbols Analyzed</div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {marketOverview.segments?.EQUITY?.total_symbols || 0}
              </div>
              <div className="text-sm text-gray-600">Equity Stocks</div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {marketOverview.segments?.COMMODITY?.total_symbols || 0}
              </div>
              <div className="text-sm text-gray-600">Commodities</div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {(marketOverview.segments?.INDEX?.total_symbols || 0) + 
                 (marketOverview.segments?.CURRENCY?.total_symbols || 0) + 
                 (marketOverview.segments?.ETF?.total_symbols || 0)}
              </div>
              <div className="text-sm text-gray-600">Indices • Currency • ETFs</div>
            </div>
          </div>
        </div>
      )}

      {/* Top Picks Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            🏆 AI Top Picks
            {selectedSegment !== 'ALL' && (
              <span className="ml-2 text-sm text-gray-500">
                • {segments.find(s => s.value === selectedSegment)?.label}
              </span>
            )}
          </h2>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
            ML-powered recommendations ranked by expected return and confidence
          </p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rank
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Symbol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Signal
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Expected Return
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Confidence
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  AI Score
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {topPicks.map((pick, index) => (
                <motion.tr
                  key={pick.symbol}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                        pick.rank <= 3 ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {pick.rank}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {pick.symbol}
                      </div>
                      <div className="text-xs text-gray-500">
                        {pick.exchange} • {pick.segment}
                      </div>
                      <div className="text-xs text-gray-400 truncate max-w-32">
                        {pick.name}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getSignalColor(pick.signal)}`}>
                      {pick.signal.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {pick.expected_return > 0 ? '+' : ''}{pick.expected_return.toFixed(1)}%
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {(pick.confidence * 100).toFixed(0)}%
                      </div>
                      <div className="ml-2 w-16 bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${pick.confidence * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {(pick.risk_score * 100).toFixed(0)}%
                      </div>
                      <div className="ml-2 w-16 bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${
                            pick.risk_score < 0.3 ? 'bg-green-500' : 
                            pick.risk_score < 0.6 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${pick.risk_score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-bold text-blue-600">
                      {pick.score.toFixed(1)}
                    </div>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Sector Analysis */}
      {sectorAnalysis.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              📊 Sector Performance Analysis
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
              AI analysis across all sectors with top picks
            </p>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sectorAnalysis.slice(0, 6).map((sector, index) => (
                <motion.div
                  key={sector.sector}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.1 }}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                      {sector.sector}
                    </h3>
                    <span className="text-xs text-gray-500">
                      {sector.metrics.symbol_count} symbols
                    </span>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Avg Return:</span>
                      <span className="text-xs font-medium text-gray-900">
                        {sector.metrics.avg_expected_return > 0 ? '+' : ''}
                        {sector.metrics.avg_expected_return.toFixed(1)}%
                      </span>
                    </div>
                    
                    <div className="flex justify-between">
                      <span className="text-xs text-gray-600">Bullish:</span>
                      <span className="text-xs font-medium text-green-600">
                        {sector.metrics.bullish_percentage.toFixed(0)}%
                      </span>
                    </div>
                    
                    <div className="pt-2 border-t border-gray-200">
                      <div className="text-xs text-gray-600 mb-1">Top Pick:</div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-blue-600">
                          {sector.top_pick.symbol}
                        </span>
                        <span className="text-xs text-gray-900">
                          {sector.top_pick.expected_return > 0 ? '+' : ''}
                          {sector.top_pick.expected_return.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ComprehensiveMLInsights;