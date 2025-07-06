import React, { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import AutoTradingSettings from './AutoTradingSettings';
import AutoTradingStatus from './AutoTradingStatus';
import AutoTradingHistory from './AutoTradingHistory';
import AutoTradingReports from './AutoTradingReports';
import ManualInterventionPanel from './ManualInterventionPanel';
import { autoTradingService } from '../../services/autoTradingService';

interface AutoTradingDashboardProps {
  className?: string;
}

interface AutoTradingStatusData {
  enabled: boolean;
  mode: string;
  subscription_plan: string;
  daily_limit: number;
  trades_today: number;
  remaining_trades: number;
  successful_trades_today: number;
  is_market_open: boolean;
  has_active_session: boolean;
  primary_broker_connected: boolean;
}

const AutoTradingDashboard: React.FC<AutoTradingDashboardProps> = ({ className }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'settings' | 'history' | 'reports'>('overview');
  const [status, setStatus] = useState<AutoTradingStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const statusData = await autoTradingService.getStatus();
      setStatus(statusData);
      setError(null);
    } catch (err) {
      setError('Failed to load auto trading status');
      console.error('Error loading auto trading status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusUpdate = () => {
    loadStatus(); // Refresh status after changes
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
    { id: 'history', label: 'History', icon: '📈' },
    { id: 'reports', label: 'Reports', icon: '📋' }
  ];

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-64 ${className}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Auto Trading</h1>
          <p className="text-gray-600">AI-powered automated trading system</p>
        </div>
        <div className="flex items-center space-x-4">
          {status && (
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${
              status.enabled && status.is_market_open 
                ? 'bg-green-100 text-green-800' 
                : 'bg-gray-100 text-gray-800'
            }`}>
              {status.enabled && status.is_market_open ? '🟢 Active' : '⭕ Inactive'}
            </div>
          )}
          <Button
            onClick={loadStatus}
            variant="outline"
            size="sm"
          >
            🔄 Refresh
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <span className="text-red-400">⚠️</span>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <AutoTradingStatus 
              status={status} 
              onRefresh={loadStatus}
            />
            {status?.enabled && (
              <ManualInterventionPanel 
                onRefresh={loadStatus}
              />
            )}
          </div>
        )}
        
        {activeTab === 'settings' && (
          <AutoTradingSettings 
            status={status}
            onUpdate={handleStatusUpdate}
          />
        )}
        
        {activeTab === 'history' && (
          <AutoTradingHistory />
        )}
        
        {activeTab === 'reports' && (
          <AutoTradingReports />
        )}
      </div>
    </div>
  );
};

export default AutoTradingDashboard;