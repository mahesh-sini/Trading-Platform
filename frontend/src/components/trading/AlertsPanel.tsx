import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Alert } from '@/types/trading';
import { 
  ExclamationTriangleIcon, 
  InformationCircleIcon, 
  XMarkIcon,
  BellIcon 
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';

interface AlertsPanelProps {
  userId: string;
}

interface AlertFilter {
  severity: 'all' | 'info' | 'warning' | 'error' | 'critical';
  type: 'all' | 'price' | 'volume' | 'technical' | 'news' | 'risk';
  timeframe: 'all' | '1h' | '24h' | '7d';
}

const AlertsPanel: React.FC<AlertsPanelProps> = ({ userId }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filter, setFilter] = useState<AlertFilter>({
    severity: 'all',
    type: 'all',
    timeframe: '24h'
  });
  const [isLoading, setIsLoading] = useState(true);
  const [expandedAlert, setExpandedAlert] = useState<string | null>(null);

  // Mock data - replace with actual API calls and WebSocket updates
  useEffect(() => {
    const fetchAlerts = async () => {
      setIsLoading(true);
      
      // Simulate API call
      setTimeout(() => {
        const mockAlerts: Alert[] = [
          {
            id: 'alert-1',
            type: 'price',
            severity: 'warning',
            title: 'Price Alert: AAPL',
            message: 'AAPL has reached your target price of $160.00',
            symbol: 'AAPL',
            condition: 'price >= 160.00',
            isActive: true,
            triggeredAt: new Date(Date.now() - 15 * 60 * 1000).toISOString(), // 15 minutes ago
            createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            metadata: {
              currentPrice: 162.45,
              targetPrice: 160.00
            }
          },
          {
            id: 'alert-2',
            type: 'volume',
            severity: 'info',
            title: 'Volume Spike: TSLA',
            message: 'TSLA volume is 3x above average',
            symbol: 'TSLA',
            condition: 'volume > 3x avg_volume',
            isActive: true,
            triggeredAt: new Date(Date.now() - 45 * 60 * 1000).toISOString(), // 45 minutes ago
            createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
            metadata: {
              currentVolume: 15750000,
              averageVolume: 5250000,
              ratio: 3.0
            }
          },
          {
            id: 'alert-3',
            type: 'risk',
            severity: 'critical',
            title: 'Risk Limit Exceeded',
            message: 'Portfolio concentration in tech sector exceeds 80%',
            condition: 'sector_exposure[tech] > 0.8',
            isActive: true,
            triggeredAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
            createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
            metadata: {
              techExposure: 0.85,
              riskLimit: 0.8
            }
          },
          {
            id: 'alert-4',
            type: 'technical',
            severity: 'warning',
            title: 'RSI Overbought: NVDA',
            message: 'NVDA RSI has crossed above 70, indicating overbought conditions',
            symbol: 'NVDA',
            condition: 'rsi > 70',
            isActive: true,
            triggeredAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
            createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
            metadata: {
              rsi: 73.2,
              threshold: 70
            }
          },
          {
            id: 'alert-5',
            type: 'news',
            severity: 'info',
            title: 'Earnings Alert: MSFT',
            message: 'Microsoft earnings report scheduled for after market close',
            symbol: 'MSFT',
            condition: 'earnings_date = today',
            isActive: true,
            triggeredAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), // 4 hours ago
            createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
            metadata: {
              earningsDate: new Date().toISOString(),
              expectedEPS: 2.45
            }
          }
        ];

        setAlerts(mockAlerts);
        setIsLoading(false);
      }, 1000);
    };

    fetchAlerts();
  }, [userId]);

  // Filter alerts based on current filter settings
  const filteredAlerts = alerts.filter(alert => {
    if (filter.severity !== 'all' && alert.severity !== filter.severity) {
      return false;
    }
    
    if (filter.type !== 'all' && alert.type !== filter.type) {
      return false;
    }
    
    if (filter.timeframe !== 'all') {
      const alertTime = new Date(alert.triggeredAt || alert.createdAt);
      const now = new Date();
      const timeDiff = now.getTime() - alertTime.getTime();
      
      switch (filter.timeframe) {
        case '1h':
          if (timeDiff > 60 * 60 * 1000) return false;
          break;
        case '24h':
          if (timeDiff > 24 * 60 * 60 * 1000) return false;
          break;
        case '7d':
          if (timeDiff > 7 * 24 * 60 * 60 * 1000) return false;
          break;
      }
    }
    
    return true;
  });

  const dismissAlert = (alertId: string) => {
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  };

  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'error':
        return <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500" />;
      case 'info':
      default:
        return <InformationCircleIcon className="w-5 h-5 text-blue-500" />;
    }
  };

  const getAlertBorderColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'border-l-red-600';
      case 'error':
        return 'border-l-red-500';
      case 'warning':
        return 'border-l-yellow-500';
      case 'info':
      default:
        return 'border-l-blue-500';
    }
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center">
            <BellIcon className="w-5 h-5 text-gray-600 dark:text-gray-300 mr-2" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Alerts ({filteredAlerts.length})
            </h3>
          </div>
          
          {/* Alert summary by severity */}
          <div className="flex space-x-2">
            {['critical', 'warning', 'info'].map(severity => {
              const count = filteredAlerts.filter(alert => alert.severity === severity).length;
              if (count === 0) return null;
              
              return (
                <div
                  key={severity}
                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                    severity === 'critical'
                      ? 'bg-red-100 text-red-800'
                      : severity === 'warning'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}
                >
                  {count}
                </div>
              );
            })}
          </div>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-3 gap-2">
          <select
            value={filter.severity}
            onChange={(e) => setFilter(prev => ({ ...prev, severity: e.target.value as any }))}
            className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>

          <select
            value={filter.type}
            onChange={(e) => setFilter(prev => ({ ...prev, type: e.target.value as any }))}
            className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="all">All Types</option>
            <option value="price">Price</option>
            <option value="volume">Volume</option>
            <option value="technical">Technical</option>
            <option value="news">News</option>
            <option value="risk">Risk</option>
          </select>

          <select
            value={filter.timeframe}
            onChange={(e) => setFilter(prev => ({ ...prev, timeframe: e.target.value as any }))}
            className="text-xs px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="all">All Time</option>
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7 Days</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      <div className="flex-1 overflow-auto">
        {filteredAlerts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">No alerts found</p>
          </div>
        ) : (
          <div className="space-y-2 p-4">
            <AnimatePresence>
              {filteredAlerts.map((alert, index) => (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                  className={`bg-white dark:bg-gray-800 border-l-4 ${getAlertBorderColor(alert.severity)} rounded-r-lg shadow-sm hover:shadow-md transition-shadow`}
                >
                  <div className="p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-3 flex-1">
                        {getAlertIcon(alert.severity)}
                        
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                              {alert.title}
                            </h4>
                            {alert.symbol && (
                              <span className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded">
                                {alert.symbol}
                              </span>
                            )}
                          </div>
                          
                          <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                            {alert.message}
                          </p>
                          
                          <div className="flex items-center justify-between mt-2">
                            <p className="text-xs text-gray-500">
                              {alert.triggeredAt 
                                ? `Triggered ${format(new Date(alert.triggeredAt), 'MMM d, HH:mm')}`
                                : `Created ${format(new Date(alert.createdAt), 'MMM d, HH:mm')}`
                              }
                            </p>
                            
                            {alert.metadata && Object.keys(alert.metadata).length > 0 && (
                              <button
                                onClick={() => setExpandedAlert(
                                  expandedAlert === alert.id ? null : alert.id
                                )}
                                className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                              >
                                {expandedAlert === alert.id ? 'Hide Details' : 'Show Details'}
                              </button>
                            )}
                          </div>

                          {/* Expanded Details */}
                          <AnimatePresence>
                            {expandedAlert === alert.id && alert.metadata && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                transition={{ duration: 0.2 }}
                                className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600"
                              >
                                <div className="space-y-1">
                                  {Object.entries(alert.metadata).map(([key, value]) => (
                                    <div key={key} className="flex justify-between text-xs">
                                      <span className="text-gray-500 capitalize">
                                        {key.replace(/([A-Z])/g, ' $1').toLowerCase()}:
                                      </span>
                                      <span className="text-gray-900 dark:text-white font-medium">
                                        {typeof value === 'number' 
                                          ? value.toLocaleString()
                                          : String(value)
                                        }
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      </div>

                      {/* Dismiss Button */}
                      <button
                        onClick={() => dismissAlert(alert.id)}
                        className="ml-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                      >
                        <XMarkIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-200 dark:border-gray-600">
        <div className="flex justify-between items-center">
          <button className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300">
            Create Alert
          </button>
          
          {filteredAlerts.length > 0 && (
            <button
              onClick={() => setAlerts([])}
              className="text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300"
            >
              Clear All
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlertsPanel;