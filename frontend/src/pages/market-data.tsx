import React from 'react';
import { Layout } from '@/components/layout/Layout';
import RealTimeQuote from '@/components/market/RealTimeQuote';

const MarketData: React.FC = () => {
  const symbols = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'KOTAKBANK'];

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Market Data</h1>
          <p className="text-gray-600">Real-time market data and analytics for Indian markets</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {symbols.map((symbol) => (
            <RealTimeQuote key={symbol} symbol={symbol} />
          ))}
        </div>
      </div>
    </Layout>
  );
};

export default MarketData;