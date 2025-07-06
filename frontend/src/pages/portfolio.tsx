import React from 'react';
import { Layout } from '@/components/layout/Layout';
import { PortfolioValue } from '@/components/portfolio/PortfolioValue';
import PortfolioSummary from '@/components/trading/widgets/PortfolioSummary';
import PositionsTable from '@/components/trading/widgets/PositionsTable';
import { Portfolio as PortfolioType } from '@/types';

const Portfolio: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = React.useState('RELIANCE');
  
  // Mock portfolio data for demo purposes
  const mockPortfolio: PortfolioType = {
    id: 'portfolio-1',
    name: 'My Portfolio',
    total_value: 125000.00,
    cash_balance: 15000.00,
    equity_value: 110000.00,
    day_change: 2500.00,
    day_change_percent: 2.04,
    total_return: 25000.00,
    total_return_percent: 25.00,
    positions: [],
    updated_at: new Date().toISOString()
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Portfolio</h1>
          <p className="text-gray-600">Manage your investment portfolio and track performance</p>
        </div>

        <PortfolioValue portfolio={mockPortfolio} />
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PortfolioSummary userId="test-user" />
          <PositionsTable userId="test-user" onSymbolSelect={setSelectedSymbol} />
        </div>
      </div>
    </Layout>
  );
};

export default Portfolio;