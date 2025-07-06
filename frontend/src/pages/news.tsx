import React from 'react';
import { Layout } from '@/components/layout/Layout';
import NewsWidget from '@/components/trading/widgets/NewsWidget';

const News: React.FC = () => {
  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Market News</h1>
          <p className="text-gray-600">Latest news and updates from Indian markets</p>
        </div>

        <NewsWidget symbols={['NIFTY', 'SENSEX', 'RELIANCE', 'TCS']} />
      </div>
    </Layout>
  );
};

export default News;