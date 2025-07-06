import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Layout } from '@/components/layout/Layout';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import StockSearchInput from '@/components/ui/StockSearchInput';
import { useMarketData, formatPrice, formatChange, getChangeColor, type LiveQuote, type MarketIndex } from '@/services/marketDataService';
import { Stock } from '@/types/trading';

const Dashboard: React.FC = () => {
  const router = useRouter();
  const marketDataService = useMarketData();
  
  // State management for Indian markets
  const [selectedStock, setSelectedStock] = useState<Stock | null>({
    symbol: 'RELIANCE',
    name: 'Reliance Industries Limited',
    exchange: 'NSE'
  });
  const [selectedTimeframe, setSelectedTimeframe] = useState('1D');
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [orderSide, setOrderSide] = useState<'BUY' | 'SELL'>('BUY');
  const [quantity, setQuantity] = useState(1);
  
  // Live market data state
  const [marketData, setMarketData] = useState<Record<string, LiveQuote>>({});
  const [indices, setIndices] = useState<MarketIndex[]>([]);
  const [mounted, setMounted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  
  // Popular Indian stocks for quick access
  const [popularStocks] = useState<Stock[]>([
    { symbol: 'RELIANCE', name: 'Reliance Industries Limited', exchange: 'NSE' },
    { symbol: 'TCS', name: 'Tata Consultancy Services Limited', exchange: 'NSE' },
    { symbol: 'INFY', name: 'Infosys Limited', exchange: 'NSE' },
    { symbol: 'HDFCBANK', name: 'HDFC Bank Limited', exchange: 'NSE' },
    { symbol: 'ICICIBANK', name: 'ICICI Bank Limited', exchange: 'NSE' },
    { symbol: 'KOTAKBANK', name: 'Kotak Mahindra Bank Limited', exchange: 'NSE' },
    { symbol: 'LT', name: 'Larsen & Toubro Limited', exchange: 'NSE' },
    { symbol: 'ITC', name: 'ITC Limited', exchange: 'NSE' },
    { symbol: 'WIPRO', name: 'Wipro Limited', exchange: 'NSE' },
    { symbol: 'MARUTI', name: 'Maruti Suzuki India Limited', exchange: 'NSE' },
    { symbol: 'BHARTIARTL', name: 'Bharti Airtel Limited', exchange: 'NSE' },
    { symbol: 'ASIANPAINT', name: 'Asian Paints Limited', exchange: 'NSE' }
  ]);
  
  const watchlist = popularStocks.map(stock => stock.symbol);
  
  // Portfolio metrics for Indian markets
  const portfolioMetrics = {
    totalValue: 1254300.50, // INR
    dayChange: 24503.30,
    dayChangePercent: 1.99,
    totalReturn: 187505.50,
    totalReturnPercent: 17.58,
    activePositions: 12,
    pendingOrders: 3,
    watchlistAlerts: 2,
  };

  // Indian stocks positions
  const topPositions = [
    { symbol: 'RELIANCE', shares: 100, value: 245675, change: 2.5, exchange: 'NSE' },
    { symbol: 'TCS', shares: 50, value: 176215, change: -1.2, exchange: 'NSE' },
    { symbol: 'INFY', shares: 75, value: 125923, change: 3.1, exchange: 'NSE' },
    { symbol: 'HDFCBANK', shares: 200, value: 316490, change: 1.8, exchange: 'NSE' },
  ];

  const recentTrades = [
    { symbol: 'RELIANCE', action: 'BUY', quantity: 20, price: 2456.75, time: '2h ago', exchange: 'NSE' },
    { symbol: 'TCS', action: 'SELL', quantity: 10, price: 3524.30, time: '4h ago', exchange: 'NSE' },
    { symbol: 'INFY', action: 'BUY', quantity: 25, price: 1678.90, time: '1d ago', exchange: 'NSE' },
  ];
  
  // Live market movers
  const [marketMovers, setMarketMovers] = useState<{
    top_gainers: Array<{symbol: string; price: number; change: number; changePercent: number}>;
    top_losers: Array<{symbol: string; price: number; change: number; changePercent: number}>;
  }>({
    top_gainers: [],
    top_losers: []
  });
  
  // Live market data initialization and updates
  useEffect(() => {
    setMounted(true);
    
    const initializeMarketData = async () => {
      try {
        setLoading(true);
        
        // Load live indices data
        const indicesData = await marketDataService.getIndices();
        setIndices(indicesData);
        
        // Load live quotes for watchlist
        const batchQuotes = await marketDataService.getBatchQuotes(watchlist);
        setMarketData(batchQuotes.quotes);
        
        // Load market movers
        const moversData = await marketDataService.getMarketMovers();
        setMarketMovers(moversData);
        
        // Subscribe to real-time updates
        await marketDataService.subscribeToRealTime(watchlist);
        
        setLastUpdate(new Date().toLocaleTimeString());
        setLoading(false);
        
      } catch (error) {
        console.error('Error initializing market data:', error);
        setLoading(false);
      }
    };
    
    initializeMarketData();
    
    // Set up periodic updates every 10 seconds
    const interval = setInterval(async () => {
      try {
        // Update watchlist quotes
        const batchQuotes = await marketDataService.getBatchQuotes(watchlist);
        setMarketData(batchQuotes.quotes);
        
        // Update indices
        const indicesData = await marketDataService.getIndices();
        setIndices(indicesData);
        
        // Update market movers (less frequently)
        if (Math.random() > 0.7) { // Update 30% of the time to reduce API calls
          const moversData = await marketDataService.getMarketMovers();
          setMarketMovers(moversData);
        }
        
        setLastUpdate(new Date().toLocaleTimeString());
      } catch (error) {
        console.error('Error updating market data:', error);
      }
    }, 10000); // Update every 10 seconds
    
    return () => {
      clearInterval(interval);
      marketDataService.stopAllStreams();
    };
  }, [watchlist, marketDataService]);
  
  // Loading state
  if (!mounted || loading) {
    return (
      <Layout>
        <div className="space-y-6">
          <div className="animate-pulse">
            <div className="h-32 bg-gray-200 rounded-lg mb-6"></div>
            <div className="h-48 bg-gray-200 rounded-lg mb-6"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
              ))}
            </div>
          </div>
          <div className="text-center text-gray-500">
            <p>Loading live market data...</p>
          </div>
        </div>
      </Layout>
    );
  }
  
  const timeframes = ['1m', '5m', '15m', '1H', '4H', '1D', '1W', '1M'];
  const selectedSymbol = selectedStock?.symbol || 'RELIANCE';
  const currentPrice = marketData[selectedSymbol]?.price || 0;
  
  // Handle stock selection from search
  const handleStockSelect = (stock: Stock) => {
    setSelectedStock(stock);
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Market Status Banner */}
        <div className="bg-gradient-to-r from-green-50 to-blue-50 p-4 rounded-lg border">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-green-700">Live Market Data</span>
              </div>
              <div className="text-sm text-gray-600">
                NSE & BSE • Last Update: {lastUpdate || 'Loading...'}
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-gray-900">
                ₹{portfolioMetrics.totalValue.toLocaleString('en-IN')}
              </div>
              <div className={`text-sm ${portfolioMetrics.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {portfolioMetrics.dayChange >= 0 ? '+' : ''}₹{Math.abs(portfolioMetrics.dayChange).toLocaleString('en-IN')} 
                ({portfolioMetrics.dayChangePercent >= 0 ? '+' : ''}{portfolioMetrics.dayChangePercent}%)
              </div>
            </div>
          </div>
        </div>

        {/* Market Indices */}
        <Card>
          <CardHeader title="Indian Market Indices" subtitle="Live NSE & BSE indices data" />
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {indices.map((index) => (
                <div key={index.symbol} className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-center space-x-2 mb-1">
                    <span className="text-sm font-medium text-gray-500">{index.symbol}</span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      index.data_source === 'live' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {index.data_source === 'live' ? 'LIVE' : 'CACHED'}
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-gray-900 mb-1">
                    {formatPrice(index.price, 'INR').replace('₹', '')}
                  </div>
                  <div className={`text-sm font-medium ${getChangeColor(index.change)}`}>
                    {formatChange(index.change, index.changePercent)}
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        {/* Quick Order Form */}
        <Card>
          <CardHeader title="Quick Trade" />
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Stock Symbol</label>
                <StockSearchInput
                  placeholder="Search Indian stocks..."
                  onStockSelect={handleStockSelect}
                  selectedStock={selectedStock}
                  showExchange={false}
                  exchanges={['NSE', 'BSE']}
                  className=""
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Type</label>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setOrderSide('BUY')}
                    className={`flex-1 py-2 px-3 rounded-md text-sm font-medium ${
                      orderSide === 'BUY' ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    BUY
                  </button>
                  <button
                    onClick={() => setOrderSide('SELL')}
                    className={`flex-1 py-2 px-3 rounded-md text-sm font-medium ${
                      orderSide === 'SELL' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-700'
                    }`}
                  >
                    SELL
                  </button>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Quantity</label>
                <input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(parseInt(e.target.value) || 0)}
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  min="1"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Price</label>
                <div className="text-center p-2 bg-gray-50 border rounded-md">
                  <span className="font-mono">{formatPrice(currentPrice)}</span>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Action</label>
                <Button 
                  variant={orderSide === 'BUY' ? 'primary' : 'outline'}
                  className="w-full"
                >
                  {orderSide} {quantity} shares
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Enhanced Portfolio Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardBody>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Portfolio Value</p>
                  <p className="text-2xl font-bold text-gray-900">
                    ₹{portfolioMetrics.totalValue.toLocaleString('en-IN')}
                  </p>
                  <p className="text-xs text-gray-500">Real-time</p>
                </div>
                <div className="p-3 bg-blue-50 rounded-full">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
                  </svg>
                </div>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Day P&L" subtitle="Today's profit & loss" />
            <CardBody>
              <div className="flex items-center justify-between">
                <div>
                  <p className={`text-3xl font-bold ${portfolioMetrics.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {portfolioMetrics.dayChange >= 0 ? '+' : ''}₹{Math.abs(portfolioMetrics.dayChange).toLocaleString('en-IN')}
                  </p>
                  <p className={`text-sm ${portfolioMetrics.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {Math.abs(portfolioMetrics.dayChangePercent)}% today
                  </p>
                </div>
                <div className={`p-3 rounded-full ${portfolioMetrics.dayChange >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                  <svg className={`w-6 h-6 ${portfolioMetrics.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Total Return" subtitle="All-time portfolio returns" />
            <CardBody>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-green-600">
                    +₹{portfolioMetrics.totalReturn.toLocaleString('en-IN')}
                  </p>
                  <p className="text-sm text-green-600">
                    +{portfolioMetrics.totalReturnPercent}% (XIRR)
                  </p>
                </div>
                <div className="p-3 bg-green-50 rounded-full">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Active Positions" subtitle="Current portfolio holdings" />
            <CardBody>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {portfolioMetrics.activePositions}
                  </p>
                  <p className="text-sm text-gray-600">
                    {portfolioMetrics.pendingOrders} pending • {portfolioMetrics.watchlistAlerts} alerts
                  </p>
                </div>
                <div className="p-3 bg-blue-50 rounded-full">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Trading Interface */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Watchlist */}
          <Card>
            <CardHeader 
              title="Popular Stocks" 
              subtitle="Click to select for trading"
            />
            <CardBody>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {/* Stock Search */}
                <div className="mb-4 pb-3 border-b border-gray-200">
                  <StockSearchInput
                    placeholder="Search any stock..."
                    onStockSelect={handleStockSelect}
                    selectedStock={null}
                    showExchange={true}
                    exchanges={['NSE', 'BSE']}
                    className=""
                  />
                </div>
                {popularStocks.map((stock) => {
                  const data = marketData[stock.symbol];
                  
                  return (
                    <div
                      key={stock.symbol}
                      className={`p-3 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
                        selectedSymbol === stock.symbol ? 'bg-blue-50 border border-blue-200' : 'border border-gray-100'
                      }`}
                      onClick={() => handleStockSelect(stock)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-900">{stock.symbol}</div>
                          <div className="text-xs text-gray-500 truncate max-w-32">
                            {data ? `${data.exchange} • Vol: ${(data.volume / 1000).toFixed(0)}K` : stock.name.slice(0, 20) + '...'}
                          </div>
                        </div>
                        <div className="text-right">
                          {data ? (
                            <>
                              <div className="font-mono text-sm text-gray-900">{formatPrice(data.price)}</div>
                              <div className={`text-xs ${getChangeColor(data.change)}`}>
                                {formatChange(data.change, data.change_percent)}
                              </div>
                            </>
                          ) : (
                            <div className="text-xs text-gray-400">Loading...</div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardBody>
          </Card>

          {/* Chart Area */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader 
                title={`${selectedSymbol} Chart`}
                subtitle={`${selectedStock?.name || selectedSymbol} • ${formatPrice(currentPrice)} • ${marketData[selectedSymbol]?.exchange || selectedStock?.exchange || 'NSE'}`}
              />
              <CardBody>
                <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-200">
                  <div className="flex space-x-1">
                    {timeframes.map((tf) => (
                      <button
                        key={tf}
                        onClick={() => setSelectedTimeframe(tf)}
                        className={`px-3 py-1 text-sm rounded ${
                          selectedTimeframe === tf
                            ? 'bg-blue-600 text-white'
                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                        }`}
                      >
                        {tf}
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="h-80 bg-gradient-to-br from-gray-50 to-blue-50 rounded-lg flex flex-col items-center justify-center border-2 border-dashed border-gray-300">
                  <div className="text-center">
                    <div className="text-4xl font-mono text-gray-900 mb-2">
                      {formatPrice(currentPrice)}
                    </div>
                    {marketData[selectedSymbol] && (
                      <div className={`text-lg ${getChangeColor(marketData[selectedSymbol].change)}`}>
                        {formatChange(marketData[selectedSymbol].change, marketData[selectedSymbol].change_percent)}
                      </div>
                    )}
                    <div className="mt-4 text-gray-500">
                      <p>Live Market Data • {selectedTimeframe} Chart</p>
                      <p className="text-sm mt-1">Real-time price updates from NSE/BSE</p>
                      {lastUpdate && (
                        <p className="text-xs mt-1">Last updated: {lastUpdate}</p>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-200">
                  <div className="text-center">
                    <div className="text-xs text-gray-500">OPEN</div>
                    <div className="font-mono text-sm">
                      {marketData[selectedSymbol] ? formatPrice(marketData[selectedSymbol].open) : '₹0.00'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">HIGH</div>
                    <div className="font-mono text-sm text-green-600">
                      {marketData[selectedSymbol] ? formatPrice(marketData[selectedSymbol].high) : '₹0.00'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">LOW</div>
                    <div className="font-mono text-sm text-red-600">
                      {marketData[selectedSymbol] ? formatPrice(marketData[selectedSymbol].low) : '₹0.00'}
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-500">VOLUME</div>
                    <div className="font-mono text-sm">
                      {marketData[selectedSymbol] ? `${((marketData[selectedSymbol].volume || 0) / 1000).toFixed(0)}K` : '0K'}
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>

          {/* Market Depth & AI Insights */}
          <div>
            <Card>
              <CardHeader title="Market Depth" />
              <CardBody>
                <div className="space-y-2">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">SELL ORDERS</div>
                    {Array.from({length: 3}, (_, i) => (
                      <div key={i} className="flex justify-between text-xs py-1 px-2 bg-red-50 rounded">
                        <span className="text-red-600">₹{(currentPrice + (i + 1) * 1.25).toFixed(2)}</span>
                        <span className="text-gray-600">{(Math.random() * 1000).toFixed(0)}</span>
                      </div>
                    )).reverse()}
                  </div>
                  
                  <div className="text-center py-2 my-2 bg-gray-100 rounded border">
                    <span className="text-lg font-mono font-bold text-gray-900">{formatPrice(currentPrice)}</span>
                  </div>
                  
                  <div>
                    <div className="text-xs text-gray-500 mb-1">BUY ORDERS</div>
                    {Array.from({length: 3}, (_, i) => (
                      <div key={i} className="flex justify-between text-xs py-1 px-2 bg-green-50 rounded">
                        <span className="text-green-600">₹{(currentPrice - (i + 1) * 1.25).toFixed(2)}</span>
                        <span className="text-gray-600">{(Math.random() * 1000).toFixed(0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardBody>
            </Card>
            
            <Card className="mt-4">
              <CardHeader title="AI Insights" />
              <CardBody>
                <div className="space-y-3">
                  <div className="p-3 bg-gradient-to-r from-green-50 to-blue-50 rounded-lg border">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{selectedSymbol}</span>
                      <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">BULLISH</span>
                    </div>
                    <div className="text-xs text-gray-600">
                      <div>Target: ₹{(currentPrice * 1.05).toFixed(2)}</div>
                      <div>Support: ₹{(currentPrice * 0.97).toFixed(2)}</div>
                      <div>Confidence: 78% • Time: 2-5 days</div>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>
        </div>

        {/* Portfolio Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card>
            <CardHeader title="Your Positions" />
            <CardBody>
              <div className="space-y-3">
                {topPositions.map((position) => (
                  <div key={position.symbol} className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{position.symbol}</p>
                        <p className="text-xs text-gray-500">{position.exchange} • {position.shares} shares</p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-gray-900">₹{position.value.toLocaleString('en-IN')}</p>
                        <p className={`text-sm ${position.change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {position.change >= 0 ? '+' : ''}{Math.abs(position.change)}%
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Market Movers" />
            <CardBody>
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-green-700 mb-2">TOP GAINERS</h4>
                  <div className="space-y-2">
                    {marketMovers.top_gainers.slice(0, 3).map((stock) => (
                      <div key={stock.symbol} className="flex justify-between text-sm">
                        <span className="font-medium">{stock.symbol}</span>
                        <div className="text-right">
                          <div className="font-mono">{formatPrice(stock.price)}</div>
                          <div className="text-green-600 text-xs">+{stock.changePercent.toFixed(2)}%</div>
                        </div>
                      </div>
                    ))}
                    {marketMovers.top_gainers.length === 0 && (
                      <div className="text-xs text-gray-400">Loading market data...</div>
                    )}
                  </div>
                </div>
                
                <div className="border-t border-gray-200 pt-3">
                  <h4 className="text-sm font-medium text-red-700 mb-2">TOP LOSERS</h4>
                  <div className="space-y-2">
                    {marketMovers.top_losers.slice(0, 3).map((stock) => (
                      <div key={stock.symbol} className="flex justify-between text-sm">
                        <span className="font-medium">{stock.symbol}</span>
                        <div className="text-right">
                          <div className="font-mono">{formatPrice(stock.price)}</div>
                          <div className="text-red-600 text-xs">{stock.changePercent.toFixed(2)}%</div>
                        </div>
                      </div>
                    ))}
                    {marketMovers.top_losers.length === 0 && (
                      <div className="text-xs text-gray-400">Loading market data...</div>
                    )}
                  </div>
                </div>
              </div>
            </CardBody>
          </Card>
          
          <Card>
            <CardHeader title="Broker Connections" />
            <CardBody>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">Zerodha Kite</p>
                      <p className="text-xs text-gray-600">Connected • Live Trading</p>
                    </div>
                  </div>
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">Primary</span>
                </div>
                
                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">ICICI Breeze</p>
                      <p className="text-xs text-gray-600">Connected • Options Trading</p>
                    </div>
                  </div>
                  <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">Secondary</span>
                </div>
                
                <div className="pt-2 border-t border-gray-200">
                  <Button variant="outline" size="sm" className="w-full text-xs">
                    + Add Broker Connection
                  </Button>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;