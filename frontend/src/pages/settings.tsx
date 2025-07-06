import React from 'react';
import { Layout } from '@/components/layout/Layout';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import BrokerConnection from '@/components/broker/BrokerConnection';

const Settings: React.FC = () => {
  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600">Manage your account and platform preferences</p>
        </div>

        {/* Broker Connections */}
        <BrokerConnection />

        {/* Account Settings */}
        <Card>
          <CardHeader title="Account Settings" subtitle="Manage your account preferences" />
          <CardBody>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Default Currency
                </label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="INR">Indian Rupee (INR)</option>
                  <option value="USD">US Dollar (USD)</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Preferred Exchange
                </label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="NSE">National Stock Exchange (NSE)</option>
                  <option value="BSE">Bombay Stock Exchange (BSE)</option>
                </select>
              </div>

              <div className="pt-4">
                <Button variant="primary">Save Settings</Button>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader title="Notifications" subtitle="Configure alert preferences" />
          <CardBody>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">Price Alerts</div>
                  <div className="text-sm text-gray-600">Get notified when stocks hit target prices</div>
                </div>
                <input type="checkbox" defaultChecked className="h-4 w-4 text-blue-600" />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">Trade Confirmations</div>
                  <div className="text-sm text-gray-600">Receive confirmations for executed trades</div>
                </div>
                <input type="checkbox" defaultChecked className="h-4 w-4 text-blue-600" />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-gray-900">Market News</div>
                  <div className="text-sm text-gray-600">Get updates on market news and events</div>
                </div>
                <input type="checkbox" className="h-4 w-4 text-blue-600" />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>
    </Layout>
  );
};

export default Settings;