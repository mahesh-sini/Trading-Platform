import React from 'react';
import { Layout } from '@/components/layout/Layout';
import PortfolioValue from '@/components/portfolio/PortfolioValue';
import PortfolioSummary from '@/components/trading/widgets/PortfolioSummary';
import PositionsTable from '@/components/trading/widgets/PositionsTable';

const Portfolio: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = React.useState('RELIANCE');

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio</h1>
          <p className="text-gray-600">Manage your investment portfolio and track performance</p>
        </div>

        <PortfolioValue />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PortfolioSummary userId="test-user" />
          <PositionsTable userId="test-user" onSymbolSelect={setSelectedSymbol} />
        </div>
      </div>
    </Layout>
  );
};

export default Portfolio;