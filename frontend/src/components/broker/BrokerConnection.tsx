import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { 
  LinkIcon, 
  CheckCircleIcon, 
  ExclamationCircleIcon,
  PlusIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';

interface Broker {
  name: string;
  display_name: string;
  description: string;
  website: string;
  credentials_required: Array<{
    field: string;
    type: string;
    description: string;
    optional?: boolean;
  }>;
  features: string[];
  markets: string[];
}

interface BrokerConnection {
  account_id: string;
  broker_name: string;
  status: string;
  balance: number;
  buying_power: number;
  currency: string;
  is_primary: boolean;
  last_sync: string | null;
  created_at: string;
  error_message?: string;
}

interface BrokerConnectionProps {
  onConnectionSuccess?: (connection: BrokerConnection) => void;
}

const BrokerConnection: React.FC<BrokerConnectionProps> = ({ onConnectionSuccess }) => {
  const [availableBrokers, setAvailableBrokers] = useState<Broker[]>([]);
  const [connections, setConnections] = useState<BrokerConnection[]>([]);
  const [selectedBroker, setSelectedBroker] = useState<Broker | null>(null);
  const [showConnectionForm, setShowConnectionForm] = useState(false);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [isConnecting, setIsConnecting] = useState(false);
  const [testResult, setTestResult] = useState<{status: string; message: string} | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAvailableBrokers();
    loadConnections();
  }, []);

  const loadAvailableBrokers = async () => {
    try {
      const response = await fetch('/api/indian-brokers/available-brokers');
      const data = await response.json();
      setAvailableBrokers(data.brokers);
    } catch (error) {
      console.error('Failed to load available brokers:', error);
    }
  };

  const loadConnections = async () => {
    try {
      const response = await fetch('/api/indian-brokers/connections');
      if (response.ok) {
        const data = await response.json();
        setConnections(data);
      }
    } catch (error) {
      console.error('Failed to load connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCredentialChange = (field: string, value: string) => {
    setCredentials(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const testConnection = async () => {
    if (!selectedBroker) return;

    setIsConnecting(true);
    setTestResult(null);

    try {
      const response = await fetch('/api/indian-brokers/test-connection', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          broker_name: selectedBroker.name,
          credentials: credentials
        }),
      });

      const result = await response.json();
      setTestResult(result);
    } catch (error) {
      setTestResult({
        status: 'failed',
        message: 'Connection test failed'
      });
    } finally {
      setIsConnecting(false);
    }
  };

  const connectBroker = async () => {
    if (!selectedBroker || !testResult || testResult.status !== 'connected') return;

    setIsConnecting(true);

    try {
      const response = await fetch('/api/indian-brokers/connect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          broker_name: selectedBroker.name,
          credentials: credentials,
          is_primary: connections.length === 0 // Make first connection primary
        }),
      });

      if (response.ok) {
        const newConnection = await response.json();
        setConnections(prev => [...prev, newConnection]);
        setShowConnectionForm(false);
        setSelectedBroker(null);
        setCredentials({});
        setTestResult(null);
        
        if (onConnectionSuccess) {
          onConnectionSuccess(newConnection);
        }
      } else {
        const error = await response.json();
        setTestResult({
          status: 'failed',
          message: error.detail || 'Failed to connect broker'
        });
      }
    } catch (error) {
      setTestResult({
        status: 'failed',
        message: 'Failed to connect broker'
      });
    } finally {
      setIsConnecting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'text-green-600 bg-green-50';
      case 'error': return 'text-red-600 bg-red-50';
      case 'pending': return 'text-yellow-600 bg-yellow-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const formatCurrency = (amount: number, currency: string = 'INR') => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  if (loading) {
    return (
      <Card>
        <CardBody>
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Connected Brokers */}
      <Card>
        <CardHeader title="Broker Connections" subtitle="Manage your Indian broker accounts" />
        <CardBody>
          {connections.length === 0 ? (
            <div className="text-center py-8">
              <LinkIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Broker Connections</h3>
              <p className="text-gray-600 mb-4">Connect your Indian broker to start trading</p>
              <Button
                onClick={() => setShowConnectionForm(true)}
                variant="primary"
                className="inline-flex items-center"
              >
                <PlusIcon className="w-5 h-5 mr-2" />
                Connect Broker
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {connections.map((connection) => (
                <div
                  key={connection.account_id}
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex-shrink-0">
                        {connection.status === 'connected' ? (
                          <CheckCircleIcon className="w-8 h-8 text-green-500" />
                        ) : (
                          <ExclamationCircleIcon className="w-8 h-8 text-red-500" />
                        )}
                      </div>
                      <div>
                        <h4 className="text-lg font-medium text-gray-900">
                          {connection.broker_name.replace('_', ' ').toUpperCase()}
                          {connection.is_primary && (
                            <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                              Primary
                            </span>
                          )}
                        </h4>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(connection.status)}`}>
                            {connection.status.toUpperCase()}
                          </span>
                          <span>Balance: {formatCurrency(connection.balance)}</span>
                          <span>Buying Power: {formatCurrency(connection.buying_power)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button variant="outline" size="sm">
                        <Cog6ToothIcon className="w-4 h-4 mr-1" />
                        Settings
                      </Button>
                    </div>
                  </div>
                  {connection.error_message && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600">
                      {connection.error_message}
                    </div>
                  )}
                </div>
              ))}
              
              <div className="pt-4 border-t border-gray-200">
                <Button
                  onClick={() => setShowConnectionForm(true)}
                  variant="outline"
                  className="w-full"
                >
                  <PlusIcon className="w-5 h-5 mr-2" />
                  Add Another Broker
                </Button>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Connection Form Modal */}
      {showConnectionForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-medium text-gray-900">Connect Indian Broker</h3>
                <button
                  onClick={() => {
                    setShowConnectionForm(false);
                    setSelectedBroker(null);
                    setCredentials({});
                    setTestResult(null);
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <span className="sr-only">Close</span>
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {!selectedBroker ? (
                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900">Choose Your Broker</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {availableBrokers.map((broker) => (
                      <div
                        key={broker.name}
                        className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 cursor-pointer transition-colors"
                        onClick={() => setSelectedBroker(broker)}
                      >
                        <h5 className="font-medium text-gray-900">{broker.display_name}</h5>
                        <p className="text-sm text-gray-600 mt-1">{broker.description}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {broker.features.map((feature) => (
                            <span
                              key={feature}
                              className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
                            >
                              {feature}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="border-b border-gray-200 pb-4">
                    <h4 className="font-medium text-gray-900">{selectedBroker.display_name}</h4>
                    <p className="text-sm text-gray-600">{selectedBroker.description}</p>
                    <a
                      href={selectedBroker.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Visit {selectedBroker.website} →
                    </a>
                  </div>

                  <div className="space-y-4">
                    <h5 className="font-medium text-gray-900">Enter Your Credentials</h5>
                    {selectedBroker.credentials_required.map((cred) => (
                      <div key={cred.field}>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          {cred.field.replace('_', ' ').toUpperCase()}
                          {!cred.optional && <span className="text-red-500 ml-1">*</span>}
                        </label>
                        <input
                          type={cred.type === 'password' ? 'password' : 'text'}
                          value={credentials[cred.field] || ''}
                          onChange={(e) => handleCredentialChange(cred.field, e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder={cred.description}
                          required={!cred.optional}
                        />
                        <p className="text-xs text-gray-500 mt-1">{cred.description}</p>
                      </div>
                    ))}
                  </div>

                  {testResult && (
                    <div className={`p-3 rounded-md ${
                      testResult.status === 'connected' 
                        ? 'bg-green-50 border border-green-200' 
                        : 'bg-red-50 border border-red-200'
                    }`}>
                      <p className={`text-sm ${
                        testResult.status === 'connected' ? 'text-green-800' : 'text-red-800'
                      }`}>
                        {testResult.message}
                      </p>
                    </div>
                  )}

                  <div className="flex space-x-4">
                    <Button
                      onClick={() => setSelectedBroker(null)}
                      variant="outline"
                      className="flex-1"
                    >
                      Back
                    </Button>
                    <Button
                      onClick={testConnection}
                      variant="outline"
                      className="flex-1"
                      disabled={isConnecting}
                    >
                      {isConnecting ? 'Testing...' : 'Test Connection'}
                    </Button>
                    <Button
                      onClick={connectBroker}
                      variant="primary"
                      className="flex-1"
                      disabled={!testResult || testResult.status !== 'connected' || isConnecting}
                    >
                      {isConnecting ? 'Connecting...' : 'Connect'}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BrokerConnection;