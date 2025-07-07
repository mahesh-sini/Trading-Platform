import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Responsive, WidthProvider } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useMarketStore } from '@/store/marketStore';
import { DashboardWidget, Stock } from '@/types/trading';
import StockSearchInput from '@/components/ui/StockSearchInput';

// Components
import PortfolioSummary from './widgets/PortfolioSummary';
import PositionsTable from './widgets/PositionsTable';
import NewsWidget from './widgets/NewsWidget';
import TradingChart from './widgets/TradingChart';
import OrderForm from './OrderForm';
import AlertsPanel from './AlertsPanel';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';

// Grid Layout
const ResponsiveGridLayout = WidthProvider(Responsive);

interface TradingDashboardProps {
  userId: string;
}

const defaultLayouts = {
  lg: [
    { i: 'portfolio', x: 0, y: 0, w: 4, h: 3 },
    { i: 'market', x: 4, y: 0, w: 4, h: 3 },
    { i: 'alerts', x: 8, y: 0, w: 4, h: 3 },
    { i: 'chart', x: 0, y: 3, w: 8, h: 6 },
    { i: 'orderform', x: 8, y: 3, w: 4, h: 6 },
    { i: 'positions', x: 0, y: 9, w: 6, h: 4 },
    { i: 'orders', x: 6, y: 9, w: 6, h: 4 },
    { i: 'watchlist', x: 0, y: 13, w: 4, h: 4 },
    { i: 'news', x: 4, y: 13, w: 4, h: 4 },
    { i: 'strategies', x: 8, y: 13, w: 4, h: 4 },
  ],
  md: [
    { i: 'portfolio', x: 0, y: 0, w: 3, h: 3 },
    { i: 'market', x: 3, y: 0, w: 3, h: 3 },
    { i: 'alerts', x: 6, y: 0, w: 3, h: 3 },
    { i: 'chart', x: 0, y: 3, w: 6, h: 6 },
    { i: 'orderform', x: 6, y: 3, w: 3, h: 6 },
    { i: 'positions', x: 0, y: 9, w: 9, h: 4 },
    { i: 'orders', x: 0, y: 13, w: 9, h: 4 },
    { i: 'watchlist', x: 0, y: 17, w: 3, h: 4 },
    { i: 'news', x: 3, y: 17, w: 3, h: 4 },
    { i: 'strategies', x: 6, y: 17, w: 3, h: 4 },
  ],
  sm: [
    { i: 'portfolio', x: 0, y: 0, w: 2, h: 3 },
    { i: 'market', x: 2, y: 0, w: 2, h: 3 },
    { i: 'alerts', x: 0, y: 3, w: 4, h: 3 },
    { i: 'chart', x: 0, y: 6, w: 4, h: 6 },
    { i: 'orderform', x: 0, y: 12, w: 4, h: 6 },
    { i: 'positions', x: 0, y: 18, w: 4, h: 4 },
    { i: 'orders', x: 0, y: 22, w: 4, h: 4 },
    { i: 'watchlist', x: 0, y: 26, w: 4, h: 4 },
    { i: 'news', x: 0, y: 30, w: 4, h: 4 },
    { i: 'strategies', x: 0, y: 34, w: 4, h: 4 },
  ],
};

const TradingDashboard: React.FC<TradingDashboardProps> = ({ userId }) => {
  const [layouts, setLayouts] = useState(defaultLayouts);
  const [isEditMode, setIsEditMode] = useState(false);
  const [selectedStock, setSelectedStock] = useState<Stock>({ 
    symbol: 'RELIANCE', 
    name: 'Reliance Industries Limited', 
    exchange: 'NSE' 
  });
  
  const selectedSymbol = selectedStock.symbol;
  
  const [popularStocks] = useState<Stock[]>([
    { symbol: 'RELIANCE', name: 'Reliance Industries Limited', exchange: 'NSE' },
    { symbol: 'TCS', name: 'Tata Consultancy Services Limited', exchange: 'NSE' },
    { symbol: 'INFY', name: 'Infosys Limited', exchange: 'NSE' },
    { symbol: 'HDFCBANK', name: 'HDFC Bank Limited', exchange: 'NSE' }
  ]);
  
  const handleStockSelect = (stock: Stock) => {
    setSelectedStock(stock);
  };
  
  const setSelectedSymbol = (symbol: string) => {
    const stock = popularStocks.find(s => s.symbol === symbol) || 
                  { symbol, name: symbol, exchange: 'NSE' as const };
    setSelectedStock(stock);
  };
  const [widgets, setWidgets] = useState<DashboardWidget[]>([
    { id: 'portfolio', type: 'portfolio_summary', title: 'Portfolio Summary', size: 'medium', position: { x: 0, y: 0, w: 4, h: 3 }, config: {}, isVisible: true },
    { id: 'market', type: 'market_overview', title: 'Market Overview', size: 'medium', position: { x: 4, y: 0, w: 4, h: 3 }, config: {}, isVisible: true },
    { id: 'alerts', type: 'alerts', title: 'Alerts', size: 'medium', position: { x: 8, y: 0, w: 4, h: 3 }, config: {}, isVisible: true },
    { id: 'chart', type: 'trading_chart', title: 'Trading Chart', size: 'large', position: { x: 0, y: 3, w: 8, h: 6 }, config: { symbol: selectedSymbol }, isVisible: true },
    { id: 'orderform', type: 'order_form', title: 'Place Order', size: 'medium', position: { x: 8, y: 3, w: 4, h: 6 }, config: {}, isVisible: true },
    { id: 'positions', type: 'positions', title: 'Positions', size: 'medium', position: { x: 0, y: 9, w: 6, h: 4 }, config: {}, isVisible: true },
    { id: 'orders', type: 'orders', title: 'Orders', size: 'medium', position: { x: 6, y: 9, w: 6, h: 4 }, config: {}, isVisible: true },
    { id: 'watchlist', type: 'watchlist', title: 'Watchlist', size: 'medium', position: { x: 0, y: 13, w: 4, h: 4 }, config: {}, isVisible: true },
    { id: 'news', type: 'news', title: 'Market News', size: 'medium', position: { x: 4, y: 13, w: 4, h: 4 }, config: {}, isVisible: true },
    { id: 'strategies', type: 'strategy_performance', title: 'Strategy Performance', size: 'medium', position: { x: 8, y: 13, w: 4, h: 4 }, config: {}, isVisible: true },
  ]);

  // WebSocket connection for real-time updates
  const webSocket = useWebSocket({
    autoConnect: false // Disable auto-connect for now to avoid connection errors
  });

  // Handle WebSocket connection and subscriptions
  useEffect(() => {
    if (webSocket.isConnected) {
      console.log('Trading dashboard WebSocket connected');
      // Subscribe to relevant channels when available
      if (webSocket.subscribe) {
        webSocket.subscribe('portfolio');
        webSocket.subscribe('orders');
        webSocket.subscribe('alerts');
        webSocket.subscribeToSymbols([selectedSymbol, ...popularStocks.map(s => s.symbol)]);
      }
    }
  }, [webSocket.isConnected, selectedSymbol, webSocket]);

  // Handle layout changes
  const handleLayoutChange = (layout: any, layouts: any) => {
    setLayouts(layouts);
    // Save to localStorage or API
    localStorage.setItem(`dashboard_layout_${userId}`, JSON.stringify(layouts));
  };

  // Load saved layout
  useEffect(() => {
    const savedLayout = localStorage.getItem(`dashboard_layout_${userId}`);
    if (savedLayout) {
      try {
        setLayouts(JSON.parse(savedLayout));
      } catch (error) {
        console.error('Failed to load saved layout:', error);
      }
    }
  }, [userId]);

  // Widget renderer
  const renderWidget = (widget: DashboardWidget) => {
    const commonProps = {
      key: widget.id,
      className: "bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden",
    };

    switch (widget.type) {
      case 'portfolio_summary':
        return (
          <div {...commonProps}>
            <PortfolioSummary userId={userId} />
          </div>
        );
      case 'market_overview':
        return (
          <div {...commonProps}>
            <Card>
              <CardHeader title="Market Overview" />
              <CardBody>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span>NIFTY</span>
                    <span className="text-green-600">+0.8%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>SENSEX</span>
                    <span className="text-green-600">+0.7%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>BANKNIFTY</span>
                    <span className="text-red-600">-0.5%</span>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>
        );
      case 'positions':
        return (
          <div {...commonProps}>
            <PositionsTable userId={userId} onSymbolSelect={setSelectedSymbol} />
          </div>
        );
      case 'orders':
        return (
          <div {...commonProps}>
            <Card>
              <CardHeader title="Recent Orders" />
              <CardBody>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>{popularStocks[0].symbol} BUY 100</span>
                    <span className="text-green-600">Filled</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>{popularStocks[1].symbol} SELL 50</span>
                    <span className="text-blue-600">Pending</span>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>
        );
      case 'watchlist':
        return (
          <div {...commonProps}>
            <Card>
              <CardHeader title="Watchlist" />
              <CardBody>
                <div className="space-y-3">
                  {/* Stock Search */}
                  <div className="pb-2 border-b border-gray-200">
                    <StockSearchInput
                      placeholder="Search stocks..."
                      onStockSelect={handleStockSelect}
                      selectedStock={null}
                      showExchange={false}
                      exchanges={['NSE', 'BSE']}
                      className="text-sm"
                    />
                  </div>
                  
                  {/* Popular Stocks */}
                  <div className="space-y-2">
                    {popularStocks.map((stock) => (
                      <div key={stock.symbol} className="flex justify-between text-sm cursor-pointer hover:bg-gray-50 p-2 rounded" onClick={() => handleStockSelect(stock)}>
                        <div>
                          <span className={stock.symbol === selectedSymbol ? 'font-bold text-blue-600' : ''}>{stock.symbol}</span>
                          <div className="text-xs text-gray-500 truncate max-w-24">{stock.name.slice(0, 20)}...</div>
                        </div>
                        <span className="text-green-600">+2.5%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>
        );
      case 'news':
        return (
          <div {...commonProps}>
            <NewsWidget symbols={[selectedSymbol]} />
          </div>
        );
      case 'trading_chart':
        return (
          <div {...commonProps}>
            <TradingChart 
              symbol={selectedSymbol}
              height={400}
              showToolbar={true}
            />
          </div>
        );
      case 'order_form':
        return (
          <div {...commonProps}>
            <OrderForm 
              symbol={selectedSymbol}
              onOrderSubmit={(order) => {
                console.log('Order submitted:', order);
              }}
            />
          </div>
        );
      case 'alerts':
        return (
          <div {...commonProps}>
            <AlertsPanel userId={userId} />
          </div>
        );
      case 'strategy_performance':
        return (
          <div {...commonProps}>
            <Card>
              <CardHeader title="Strategy Performance" />
              <CardBody>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>ML Strategy</span>
                    <span className="text-green-600">+15.2%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Momentum</span>
                    <span className="text-green-600">+8.7%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Mean Reversion</span>
                    <span className="text-red-600">-2.1%</span>
                  </div>
                </div>
              </CardBody>
            </Card>
          </div>
        );
      default:
        return (
          <div {...commonProps}>
            <div className="p-4">
              <h3 className="text-lg font-semibold">{widget.title}</h3>
              <p className="text-gray-500">Widget type not implemented</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Trading Dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Real-time trading and portfolio management
            </p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Connection Status */}
            <div className="flex items-center space-x-2">
              <div 
                className={`w-2 h-2 rounded-full ${
                  webSocket.isConnected ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {webSocket.isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>

            {/* Edit Mode Toggle */}
            <button
              onClick={() => setIsEditMode(!isEditMode)}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isEditMode
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                  : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {isEditMode ? 'Exit Edit Mode' : 'Customize Layout'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Dashboard */}
      <div className="p-6">
        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          onLayoutChange={handleLayoutChange}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 9, sm: 4, xs: 2, xxs: 1 }}
          rowHeight={60}
          isDraggable={isEditMode}
          isResizable={isEditMode}
          margin={[16, 16]}
          containerPadding={[0, 0]}
          useCSSTransforms={true}
        >
          {widgets.filter(widget => widget.isVisible).map(renderWidget)}
        </ResponsiveGridLayout>
      </div>

      {/* Edit Mode Overlay */}
      {isEditMode && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black bg-opacity-20 z-50 pointer-events-none"
        >
          <div className="absolute top-4 left-1/2 transform -translate-x-1/2 pointer-events-auto">
            <div className="bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg">
              <p className="text-sm font-medium">
                Drag and resize widgets to customize your dashboard
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default TradingDashboard;