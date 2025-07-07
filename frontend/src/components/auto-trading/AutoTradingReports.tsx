import React, { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { reportsService } from '../../services/reportsService';

interface ReportSummary {
  period_start: string;
  period_end: string;
  total_trades: number;
  successful_trades: number;
  failed_trades: number;
  total_volume: number;
  total_pnl: number;
  success_rate: number;
  average_trade_size: number;
  best_performing_symbol?: string;
  worst_performing_symbol?: string;
}

interface AutoTradingReportsProps {
  className?: string;
}

const AutoTradingReports: React.FC<AutoTradingReportsProps> = ({ className }) => {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    format: 'csv' as 'csv' | 'json'
  });

  useEffect(() => {
    // Set default dates (last 30 days)
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 30);
    
    setFilters(prev => ({
      ...prev,
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0]
    }));
  }, []);

  useEffect(() => {
    if (filters.startDate && filters.endDate) {
      loadSummary();
    }
  }, [filters.startDate, filters.endDate]);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const summaryData = await reportsService.getAutoTradesSummary(
        filters.startDate,
        filters.endDate
      );
      setSummary(summaryData);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load report summary');
      console.error('Error loading summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setLoading(true);
      await reportsService.exportAutoTrades({
        format: filters.format,
        start_date: filters.startDate,
        end_date: filters.endDate
      });
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to export report');
      console.error('Error exporting report:', err);
    } finally {
      setLoading(false);
    }
  };

  const getEODSummary = async () => {
    try {
      setLoading(true);
      const eodData = await reportsService.getEODSummary();
      // You could show this in a modal or separate component
      console.log('EOD Summary:', eodData);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to get EOD summary');
      console.error('Error getting EOD summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`;
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Report Filters */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Report Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Start Date
              </label>
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => setFilters(prev => ({ ...prev, startDate: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                End Date
              </label>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => setFilters(prev => ({ ...prev, endDate: e.target.value }))}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Export Format
              </label>
              <select
                value={filters.format}
                onChange={(e) => setFilters(prev => ({ ...prev, format: e.target.value as 'csv' | 'json' }))}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
            </div>

            <div className="flex items-end space-x-2">
              <Button onClick={loadSummary} variant="outline" className="flex-1">
                🔄 Refresh
              </Button>
              <Button onClick={handleExport} className="flex-1">
                📥 Export
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <span className="text-red-400 mr-3">⚠️</span>
            <div>
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Quick Reports</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button onClick={getEODSummary} variant="outline" className="h-20">
              <div className="text-center">
                <div className="text-2xl mb-1">📅</div>
                <div className="text-sm">End of Day Summary</div>
              </div>
            </Button>
            
            <Button 
              onClick={() => {
                const today = new Date().toISOString().split('T')[0];
                setFilters(prev => ({ ...prev, startDate: today, endDate: today }));
              }}
              variant="outline" 
              className="h-20"
            >
              <div className="text-center">
                <div className="text-2xl mb-1">📊</div>
                <div className="text-sm">Today&apos;s Trades</div>
              </div>
            </Button>
            
            <Button 
              onClick={() => {
                const endDate = new Date();
                const startDate = new Date();
                startDate.setDate(startDate.getDate() - 7);
                setFilters(prev => ({
                  ...prev,
                  startDate: startDate.toISOString().split('T')[0],
                  endDate: endDate.toISOString().split('T')[0]
                }));
              }}
              variant="outline" 
              className="h-20"
            >
              <div className="text-center">
                <div className="text-2xl mb-1">📈</div>
                <div className="text-sm">Weekly Report</div>
              </div>
            </Button>
          </div>
        </div>
      </Card>

      {/* Report Summary */}
      {loading ? (
        <Card>
          <div className="p-6 flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </Card>
      ) : summary ? (
        <Card>
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">
                Report Summary ({summary.period_start} to {summary.period_end})
              </h3>
              <span className="text-sm text-gray-500">
                {summary.total_trades} total trades
              </span>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-2xl font-bold text-blue-600">
                  {summary.total_trades}
                </div>
                <div className="text-sm text-blue-800">Total Trades</div>
              </div>
              
              <div className="text-center p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="text-2xl font-bold text-green-600">
                  {summary.successful_trades}
                </div>
                <div className="text-sm text-green-800">Successful</div>
              </div>
              
              <div className="text-center p-4 bg-red-50 rounded-lg border border-red-200">
                <div className="text-2xl font-bold text-red-600">
                  {summary.failed_trades}
                </div>
                <div className="text-sm text-red-800">Failed</div>
              </div>
              
              <div className="text-center p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div className="text-2xl font-bold text-purple-600">
                  {formatPercentage(summary.success_rate)}
                </div>
                <div className="text-sm text-purple-800">Success Rate</div>
              </div>
            </div>

            {/* Financial Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium text-gray-700 mb-2">Total Volume</h4>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(summary.total_volume)}
                </div>
              </div>
              
              <div className={`p-4 rounded-lg ${summary.total_pnl >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                <h4 className="font-medium text-gray-700 mb-2">Total P&L</h4>
                <div className={`text-2xl font-bold ${summary.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(summary.total_pnl)}
                </div>
              </div>
              
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium text-gray-700 mb-2">Avg Trade Size</h4>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(summary.average_trade_size)}
                </div>
              </div>
            </div>

            {/* Best/Worst Performers */}
            {(summary.best_performing_symbol || summary.worst_performing_symbol) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {summary.best_performing_symbol && (
                  <div className="bg-green-50 border border-green-200 p-4 rounded-lg">
                    <h4 className="font-medium text-green-800 mb-2">🏆 Best Performer</h4>
                    <div className="text-lg font-bold text-green-900">
                      {summary.best_performing_symbol}
                    </div>
                  </div>
                )}
                
                {summary.worst_performing_symbol && (
                  <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
                    <h4 className="font-medium text-red-800 mb-2">📉 Worst Performer</h4>
                    <div className="text-lg font-bold text-red-900">
                      {summary.worst_performing_symbol}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </Card>
      ) : null}

      {/* Report Actions */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Report Actions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button 
              onClick={handleExport}
              disabled={loading}
              className="h-16"
            >
              <div className="text-center">
                <div className="text-xl mb-1">📥</div>
                <div className="text-sm">Download Detailed Report</div>
              </div>
            </Button>
            
            <Button 
              variant="outline"
              onClick={() => {
                // Generate PDF report (would need additional implementation)
                alert('PDF generation coming soon!');
              }}
              className="h-16"
            >
              <div className="text-center">
                <div className="text-xl mb-1">📄</div>
                <div className="text-sm">Generate PDF Report</div>
              </div>
            </Button>
            
            <Button 
              variant="outline"
              onClick={() => {
                // Email report (would need additional implementation)
                alert('Email report feature coming soon!');
              }}
              className="h-16"
            >
              <div className="text-center">
                <div className="text-xl mb-1">📧</div>
                <div className="text-sm">Email Report</div>
              </div>
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AutoTradingReports;