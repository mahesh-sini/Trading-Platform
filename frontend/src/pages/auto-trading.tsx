import React from 'react';
import { NextPage } from 'next';
import Head from 'next/head';
import { Layout } from '../components/layout/Layout';
import AutoTradingDashboard from '../components/auto-trading/AutoTradingDashboard';

const AutoTradingPage: NextPage = () => {
  return (
    <>
      <Head>
        <title>Auto Trading - AI Trading Platform</title>
        <meta 
          name="description" 
          content="AI-powered automatic trading system with real-time execution and comprehensive reporting"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <Layout>
        <div className="container mx-auto px-4 py-8">
          <AutoTradingDashboard />
        </div>
      </Layout>
    </>
  );
};

export default AutoTradingPage;