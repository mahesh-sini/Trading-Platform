import React from 'react';
import { Layout } from '@/components/layout/Layout';
import WatchlistWidget from '@/components/trading/widgets/WatchlistWidget';

const Watchlists: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = React.useState('RELIANCE');

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Watchlists</h1>
          <p className="text-gray-600">Monitor your favorite stocks and symbols</p>
        </div>

        <WatchlistWidget 
          userId="test-user"
          onSymbolSelect={setSelectedSymbol}
          selectedSymbol={selectedSymbol}
        />
      </div>
    </Layout>
  );
};

export default Watchlists;