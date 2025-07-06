import React, { useState, useEffect } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { autoTradingService } from '../../services/autoTradingService';

interface AutoTradingSettingsProps {
  status: {
    enabled: boolean;
    mode: string;
    subscription_plan: string;
    primary_broker_connected: boolean;
  } | null;
  onUpdate: () => void;
}

const AutoTradingSettings: React.FC<AutoTradingSettingsProps> = ({ status, onUpdate }) => {
  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState('conservative');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (status) {
      setEnabled(status.enabled);
      setMode(status.mode);
    }
  }, [status]);

  const handleSave = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      await autoTradingService.updateSettings({
        enabled,
        mode
      });

      setSuccess('Settings updated successfully!');
      onUpdate(); // Refresh parent component
    } catch (err: any) {
      setError(err.message || 'Failed to update settings');
      console.error('Error updating settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnable = async () => {
    const newEnabled = !enabled;
    setEnabled(newEnabled);
    
    // Auto-save when toggling enabled state
    try {
      setLoading(true);
      setError(null);
      
      if (newEnabled) {
        await autoTradingService.enable({ enabled: true, mode });
      } else {
        await autoTradingService.disable();
      }
      
      setSuccess(`Auto trading ${newEnabled ? 'enabled' : 'disabled'} successfully!`);
      onUpdate();
    } catch (err: any) {
      setError(err.message || 'Failed to update auto trading status');
      setEnabled(!newEnabled); // Revert on error
    } finally {
      setLoading(false);
    }
  };

  const tradingModes = [
    {
      id: 'conservative',
      name: 'Conservative',
      description: 'Lower risk, higher confidence requirements (80% min confidence, 2% min return)',
      risk: 'Low',
      color: 'text-green-600 bg-green-50 border-green-200'
    },
    {
      id: 'moderate',
      name: 'Moderate',
      description: 'Balanced risk and return (70% min confidence, 1.5% min return)',
      risk: 'Medium',
      color: 'text-yellow-600 bg-yellow-50 border-yellow-200'
    },
    {
      id: 'aggressive',
      name: 'Aggressive',
      description: 'Higher risk, lower confidence requirements (60% min confidence, 1% min return)',
      risk: 'High',
      color: 'text-red-600 bg-red-50 border-red-200'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Status Messages */}
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

      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex">
            <span className="text-green-400 mr-3">✅</span>
            <div>
              <h3 className="text-sm font-medium text-green-800">Success</h3>
              <p className="mt-1 text-sm text-green-700">{success}</p>
            </div>
          </div>
        </div>
      )}

      {/* Prerequisites Check */}
      {!status?.primary_broker_connected && (
        <Card>
          <div className="p-6">
            <h3 className="text-lg font-semibold text-red-600 mb-4">⚠️ Setup Required</h3>
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700 mb-4">
                To enable auto trading, you need to:
              </p>
              <ul className="list-disc list-inside text-red-700 space-y-2">
                <li>Connect your broker account with API credentials</li>
                <li>Have an active subscription plan that supports auto trading</li>
                <li>Verify your identity and trading permissions</li>
              </ul>
              <Button className="mt-4" variant="outline">
                Set Up Broker Connection
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Auto Trading Toggle */}
      <Card>
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Auto Trading</h3>
              <p className="text-gray-600">Enable or disable automatic trade execution</p>
            </div>
            <div className="flex items-center">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={handleToggleEnable}
                  disabled={loading || !status?.primary_broker_connected}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
              <span className="ml-3 text-sm font-medium">
                {enabled ? 'Enabled' : 'Disabled'}
              </span>
            </div>
          </div>

          {enabled && (
            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-700">
                🚀 Auto trading is enabled. The system will automatically execute trades during market hours based on AI predictions.
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Trading Mode Selection */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Trading Mode</h3>
          <p className="text-gray-600 mb-6">
            Choose your risk tolerance and trading strategy approach
          </p>

          <div className="space-y-4">
            {tradingModes.map((modeOption) => (
              <div
                key={modeOption.id}
                className={`border rounded-lg p-4 cursor-pointer transition-all ${
                  mode === modeOption.id
                    ? modeOption.color + ' border-2'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setMode(modeOption.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center">
                    <input
                      type="radio"
                      name="trading-mode"
                      value={modeOption.id}
                      checked={mode === modeOption.id}
                      onChange={() => setMode(modeOption.id)}
                      className="mr-3 text-blue-600"
                    />
                    <div>
                      <h4 className="font-medium">{modeOption.name}</h4>
                      <p className="text-sm text-gray-600 mt-1">
                        {modeOption.description}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    modeOption.risk === 'Low' ? 'bg-green-100 text-green-800' :
                    modeOption.risk === 'Medium' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {modeOption.risk} Risk
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Additional Settings */}
      <Card>
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Advanced Settings</h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b border-gray-200">
              <div>
                <h4 className="font-medium">Maximum Daily Trades</h4>
                <p className="text-sm text-gray-600">Based on your subscription plan</p>
              </div>
              <span className="font-medium text-gray-900">
                {status?.subscription_plan === 'basic' ? '10' :
                 status?.subscription_plan === 'pro' ? '50' :
                 status?.subscription_plan === 'enterprise' ? '1000' : '0'} trades
              </span>
            </div>

            <div className="flex items-center justify-between py-3 border-b border-gray-200">
              <div>
                <h4 className="font-medium">Market Hours</h4>
                <p className="text-sm text-gray-600">Auto trading active during these hours</p>
              </div>
              <span className="font-medium text-gray-900">9:15 AM - 3:30 PM IST</span>
            </div>

            <div className="flex items-center justify-between py-3">
              <div>
                <h4 className="font-medium">Maximum Fund Usage</h4>
                <p className="text-sm text-gray-600">Percentage of available funds to use</p>
              </div>
              <span className="font-medium text-gray-900">80%</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end space-x-4">
        <Button
          variant="outline"
          onClick={() => {
            if (status) {
              setEnabled(status.enabled);
              setMode(status.mode);
              setError(null);
              setSuccess(null);
            }
          }}
        >
          Reset
        </Button>
        
        <Button
          onClick={handleSave}
          disabled={loading || !status?.primary_broker_connected}
          className="min-w-[120px]"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Saving...
            </>
          ) : (
            'Save Settings'
          )}
        </Button>
      </div>
    </div>
  );
};

export default AutoTradingSettings;