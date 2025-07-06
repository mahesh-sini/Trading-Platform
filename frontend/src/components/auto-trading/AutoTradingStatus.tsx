import React from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';

interface AutoTradingStatusProps {
  status: {
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
  } | null;
  onRefresh: () => void;
}

import { autoTradingService } from '../../services/autoTradingService';

const AutoTradingStatus: React.FC<AutoTradingStatusProps> = ({ status, onRefresh }) => {
  const handleEmergencyStop = async () => {
    if (!confirm('⚠️ This will immediately stop all auto-trading activity. Are you sure?')) {
      return;
    }
    
    try {
      await autoTradingService.emergencyStop('Market volatility - manual intervention');
      alert('🚨 Emergency stop executed successfully!');
      onRefresh();
    } catch (error) {
      alert('Failed to execute emergency stop. Please try again.');
      console.error('Emergency stop error:', error);
    }
  };

  const handlePauseTrading = async (minutes: number) => {
    try {
      await autoTradingService.pauseTrading(minutes, 'Manual pause for review');
      alert(`⏸️ Auto-trading paused for ${minutes} minutes.`);
      onRefresh();
    } catch (error) {
      alert('Failed to pause trading. Please try again.');
      console.error('Pause trading error:', error);
    }
  };

  const handleResumeTrading = async () => {
    try {
      await autoTradingService.resumeTrading();
      alert('▶️ Auto-trading resumed successfully!');
      onRefresh();
    } catch (error) {
      alert('Failed to resume trading. Please try again.');
      console.error('Resume trading error:', error);
    }
  };

  if (!status) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No status data available</p>
        <Button onClick={onRefresh} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  const getStatusColor = (enabled: boolean, marketOpen: boolean, brokerConnected: boolean) => {
    if (!brokerConnected) return 'text-red-600';
    if (!enabled) return 'text-gray-600';
    if (!marketOpen) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getStatusMessage = () => {
    if (!status.primary_broker_connected) return 'Broker not connected';
    if (!status.enabled) return 'Auto trading disabled';
    if (!status.is_market_open) return 'Market closed - trading paused';
    if (status.remaining_trades <= 0) return 'Daily trade limit reached';
    return 'Active and monitoring market';
  };

  const successRate = status.trades_today > 0 
    ? Math.round((status.successful_trades_today / status.trades_today) * 100)
    : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {/* Main Status Card */}
      <Card className="lg:col-span-2">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Auto Trading Status</h3>
            <div className={`flex items-center ${getStatusColor(status.enabled, status.is_market_open, status.primary_broker_connected)}`}>
              <div className="w-3 h-3 rounded-full bg-current mr-2 animate-pulse"></div>
              <span className="font-medium">{getStatusMessage()}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{status.trades_today}</div>
              <div className="text-sm text-gray-600">Trades Today</div>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{status.successful_trades_today}</div>
              <div className="text-sm text-gray-600">Successful</div>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{status.remaining_trades}</div>
              <div className="text-sm text-gray-600">Remaining</div>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600">{successRate}%</div>
              <div className="text-sm text-gray-600">Success Rate</div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">Daily Limit:</span>
              <span className="font-medium">{status.daily_limit} trades</span>
            </div>
            <div className="flex items-center justify-between text-sm mt-1">
              <span className="text-gray-600">Trading Mode:</span>
              <span className="font-medium capitalize">{status.mode}</span>
            </div>
            <div className="flex items-center justify-between text-sm mt-1">
              <span className="text-gray-600">Subscription:</span>
              <span className="font-medium capitalize">{status.subscription_plan}</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Manual Controls Card */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Manual Controls</h3>
          
          <div className="space-y-3">
            <Button
              onClick={() => handleEmergencyStop()}
              variant="outline"
              className="w-full border-red-300 text-red-700 hover:bg-red-50"
            >
              🚨 Emergency Stop
            </Button>
            
            <Button
              onClick={() => handlePauseTrading(30)}
              variant="outline"
              className="w-full border-yellow-300 text-yellow-700 hover:bg-yellow-50"
            >
              ⏸️ Pause (30 min)
            </Button>
            
            <Button
              onClick={() => handleResumeTrading()}
              variant="outline"
              className="w-full border-green-300 text-green-700 hover:bg-green-50"
            >
              ▶️ Resume Trading
            </Button>
          </div>

          <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded-md">
            <p className="text-xs text-gray-600">
              💡 Use manual controls to intervene when market conditions change or you want to override the AI system.
            </p>
          </div>
        </div>
      </Card>

      {/* System Health Card */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">System Health</h3>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Auto Trading</span>
              <div className={`flex items-center ${status.enabled ? 'text-green-600' : 'text-gray-400'}`}>
                <div className="w-2 h-2 rounded-full bg-current mr-2"></div>
                <span className="text-xs font-medium">
                  {status.enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Market Status</span>
              <div className={`flex items-center ${status.is_market_open ? 'text-green-600' : 'text-yellow-600'}`}>
                <div className="w-2 h-2 rounded-full bg-current mr-2"></div>
                <span className="text-xs font-medium">
                  {status.is_market_open ? 'Open' : 'Closed'}
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Broker Connection</span>
              <div className={`flex items-center ${status.primary_broker_connected ? 'text-green-600' : 'text-red-600'}`}>
                <div className="w-2 h-2 rounded-full bg-current mr-2"></div>
                <span className="text-xs font-medium">
                  {status.primary_broker_connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Active Session</span>
              <div className={`flex items-center ${status.has_active_session ? 'text-green-600' : 'text-gray-400'}`}>
                <div className="w-2 h-2 rounded-full bg-current mr-2"></div>
                <span className="text-xs font-medium">
                  {status.has_active_session ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>

          {!status.primary_broker_connected && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-xs text-red-700">
                ⚠️ Please connect your broker account to enable auto trading.
              </p>
            </div>
          )}

          {status.primary_broker_connected && !status.enabled && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
              <p className="text-xs text-blue-700">
                💡 Auto trading is ready. Enable it in Settings to start.
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Today's Progress */}
      <Card className="lg:col-span-3">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Today's Progress</h3>
          
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div 
              className="bg-blue-600 h-2 rounded-full" 
              style={{ width: `${(status.trades_today / status.daily_limit) * 100}%` }}
            ></div>
          </div>
          
          <div className="flex justify-between text-sm text-gray-600">
            <span>{status.trades_today} trades executed</span>
            <span>{status.daily_limit} daily limit</span>
          </div>

          {status.remaining_trades <= 5 && status.remaining_trades > 0 && (
            <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <p className="text-xs text-yellow-700">
                ⚡ You have {status.remaining_trades} trades remaining today.
              </p>
            </div>
          )}

          {status.remaining_trades === 0 && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-xs text-red-700">
                🚫 Daily trade limit reached. Auto trading will resume tomorrow.
              </p>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default AutoTradingStatus;