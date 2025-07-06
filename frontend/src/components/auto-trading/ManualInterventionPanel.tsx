import React, { useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { autoTradingService } from '../../services/autoTradingService';

interface ManualInterventionPanelProps {
  onRefresh: () => void;
  className?: string;
}

const ManualInterventionPanel: React.FC<ManualInterventionPanelProps> = ({ onRefresh, className }) => {
  const [loading, setLoading] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [customPauseDuration, setCustomPauseDuration] = useState(30);
  const [customReason, setCustomReason] = useState('');

  const handleQuickAction = async (action: 'emergency' | 'pause30' | 'pause60' | 'resume') => {
    setLoading(true);
    try {
      switch (action) {
        case 'emergency':
          if (confirm('🚨 EMERGENCY STOP\n\nThis will immediately halt ALL auto-trading activity and cancel pending trades.\n\nAre you absolutely sure?')) {
            await autoTradingService.emergencyStop('Emergency stop - manual intervention');
            alert('🚨 Emergency stop executed! All auto-trading has been halted.');
          }
          break;
        
        case 'pause30':
          await autoTradingService.pauseTrading(30, 'Quick pause - 30 minutes');
          alert('⏸️ Auto-trading paused for 30 minutes.');
          break;
        
        case 'pause60':
          await autoTradingService.pauseTrading(60, 'Quick pause - 1 hour');
          alert('⏸️ Auto-trading paused for 1 hour.');
          break;
        
        case 'resume':
          if (confirm('▶️ Resume auto-trading?\n\nThis will restart automatic trade execution.')) {
            await autoTradingService.resumeTrading();
            alert('▶️ Auto-trading resumed successfully!');
          }
          break;
      }
      onRefresh();
    } catch (error: any) {
      alert(`Action failed: ${error.message || 'Unknown error'}`);
      console.error(`${action} action error:`, error);
    } finally {
      setLoading(false);
    }
  };

  const handleCustomPause = async () => {
    if (customPauseDuration < 1 || customPauseDuration > 1440) {
      alert('Please enter a duration between 1 and 1440 minutes (24 hours).');
      return;
    }

    setLoading(true);
    try {
      await autoTradingService.pauseTrading(
        customPauseDuration, 
        customReason || `Custom pause - ${customPauseDuration} minutes`
      );
      alert(`⏸️ Auto-trading paused for ${customPauseDuration} minutes.`);
      setCustomReason('');
      onRefresh();
    } catch (error: any) {
      alert(`Failed to pause trading: ${error.message || 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className={className}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Manual Intervention</h3>
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">Override AI decisions</span>
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              {showAdvanced ? '🔼 Simple' : '🔽 Advanced'}
            </button>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <Button
            onClick={() => handleQuickAction('emergency')}
            disabled={loading}
            className="bg-red-600 hover:bg-red-700 text-white border-0"
          >
            🚨 Emergency Stop
          </Button>
          
          <Button
            onClick={() => handleQuickAction('resume')}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 text-white border-0"
          >
            ▶️ Resume
          </Button>
          
          <Button
            onClick={() => handleQuickAction('pause30')}
            disabled={loading}
            variant="outline"
            className="border-yellow-300 text-yellow-700 hover:bg-yellow-50"
          >
            ⏸️ Pause 30min
          </Button>
          
          <Button
            onClick={() => handleQuickAction('pause60')}
            disabled={loading}
            variant="outline"
            className="border-yellow-300 text-yellow-700 hover:bg-yellow-50"
          >
            ⏸️ Pause 1hr
          </Button>
        </div>

        {/* Advanced Controls */}
        {showAdvanced && (
          <div className="border-t border-gray-200 pt-4">
            <h4 className="font-medium mb-3">Custom Pause Duration</h4>
            
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <label className="text-sm font-medium text-gray-700 w-20">
                  Duration:
                </label>
                <input
                  type="number"
                  min="1"
                  max="1440"
                  value={customPauseDuration}
                  onChange={(e) => setCustomPauseDuration(Number(e.target.value))}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Minutes (1-1440)"
                />
                <span className="text-sm text-gray-500">minutes</span>
              </div>
              
              <div className="flex items-start space-x-3">
                <label className="text-sm font-medium text-gray-700 w-20 mt-2">
                  Reason:
                </label>
                <textarea
                  value={customReason}
                  onChange={(e) => setCustomReason(e.target.value)}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Optional reason for pause..."
                  rows={2}
                />
              </div>
              
              <Button
                onClick={handleCustomPause}
                disabled={loading}
                className="w-full"
              >
                {loading ? 'Pausing...' : 'Apply Custom Pause'}
              </Button>
            </div>
          </div>
        )}

        {/* Warning Message */}
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-md">
          <div className="flex items-start">
            <span className="text-amber-400 mr-2 mt-0.5">⚠️</span>
            <div>
              <p className="text-sm text-amber-800 font-medium">Manual Intervention Guidelines:</p>
              <ul className="text-xs text-amber-700 mt-1 space-y-1">
                <li>• <strong>Emergency Stop</strong>: Use when market conditions are extremely volatile</li>
                <li>• <strong>Pause</strong>: Use when you want to review trades or market conditions</li>
                <li>• <strong>Resume</strong>: Use to restart after pause (market hours only)</li>
                <li>• All actions are logged and can be reviewed in trade history</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Current Status */}
        <div className="mt-4 text-center">
          <p className="text-xs text-gray-500">
            Manual controls override AI decisions immediately.
            <br />
            System will respect your intervention until manually resumed.
          </p>
        </div>
      </div>
    </Card>
  );
};

export default ManualInterventionPanel;