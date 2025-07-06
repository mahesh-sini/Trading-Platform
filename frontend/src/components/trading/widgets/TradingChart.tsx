import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, LineData, UTCTimestamp } from 'lightweight-charts';
import { useMarketStore } from '@/store/marketStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ChartConfig, CandlestickData as CustomCandlestickData } from '@/types/trading';
import { format } from 'date-fns';

interface TradingChartProps {
  symbol: string;
  height?: number;
  showToolbar?: boolean;
  config?: Partial<ChartConfig>;
}

interface ChartIndicator {
  id: string;
  name: string;
  type: 'overlay' | 'oscillator';
  series?: ISeriesApi<'Line'>;
  visible: boolean;
}

const TradingChart: React.FC<TradingChartProps> = ({
  symbol,
  height = 400,
  showToolbar = true,
  config = {}
}) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  
  const [chartConfig, setChartConfig] = useState<ChartConfig>({
    timeframe: '1d',
    indicators: ['volume'],
    overlays: [],
    style: 'candlestick',
    ...config
  });
  
  const [indicators, setIndicators] = useState<ChartIndicator[]>([
    { id: 'sma20', name: 'SMA (20)', type: 'overlay', visible: false },
    { id: 'sma50', name: 'SMA (50)', type: 'overlay', visible: false },
    { id: 'ema20', name: 'EMA (20)', type: 'overlay', visible: false },
    { id: 'rsi', name: 'RSI (14)', type: 'oscillator', visible: false },
    { id: 'macd', name: 'MACD', type: 'oscillator', visible: false },
  ]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { quotes } = useMarketStore();
  const webSocket = useWebSocket();

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#e0e0e0' },
        horzLines: { color: '#e0e0e0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#cccccc',
      },
      timeScale: {
        borderColor: '#cccccc',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Create candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    // Create volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    });

    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    volumeSeriesRef.current = volumeSeries;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [height]);

  // Load historical data
  const loadHistoricalData = useCallback(async () => {
    if (!symbol) return;

    setIsLoading(true);
    setError(null);

    try {
      // This would be replaced with actual API call
      const response = await fetch(
        `/api/market-data/historical?symbol=${symbol}&timeframe=${chartConfig.timeframe}&limit=100`
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch historical data');
      }

      const data: CustomCandlestickData[] = await response.json();
      
      // Convert data format for lightweight-charts
      const candlestickData: CandlestickData[] = data.map(item => ({
        time: (new Date(item.time).getTime() / 1000) as UTCTimestamp,
        open: item.open,
        high: item.high,
        low: item.low,
        close: item.close,
      }));

      const volumeData = data.map(item => ({
        time: (new Date(item.time).getTime() / 1000) as UTCTimestamp,
        value: item.volume || 0,
        color: item.close >= item.open ? '#26a69a' : '#ef5350',
      }));

      if (candlestickSeriesRef.current && volumeSeriesRef.current) {
        candlestickSeriesRef.current.setData(candlestickData);
        volumeSeriesRef.current.setData(volumeData);
      }

      // Calculate and add indicators
      updateIndicators(data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load chart data');
    } finally {
      setIsLoading(false);
    }
  }, [symbol, chartConfig.timeframe]);

  // Update indicators
  const updateIndicators = useCallback((data: CustomCandlestickData[]) => {
    if (!chartRef.current) return;

    indicators.forEach(indicator => {
      if (!indicator.visible) return;

      let indicatorData: LineData[] = [];

      switch (indicator.id) {
        case 'sma20':
          indicatorData = calculateSMA(data, 20);
          break;
        case 'sma50':
          indicatorData = calculateSMA(data, 50);
          break;
        case 'ema20':
          indicatorData = calculateEMA(data, 20);
          break;
        case 'rsi':
          indicatorData = calculateRSI(data, 14);
          break;
        case 'macd':
          indicatorData = calculateMACD(data);
          break;
      }

      if (indicator.series) {
        indicator.series.setData(indicatorData);
      } else if (indicatorData.length > 0) {
        const series = chartRef.current!.addLineSeries({
          color: getIndicatorColor(indicator.id),
          lineWidth: 2,
          title: indicator.name,
        });
        series.setData(indicatorData);
        indicator.series = series;
      }
    });
  }, [indicators]);

  // Technical Analysis Calculations
  const calculateSMA = (data: CustomCandlestickData[], period: number): LineData[] => {
    const result: LineData[] = [];
    
    for (let i = period - 1; i < data.length; i++) {
      const sum = data.slice(i - period + 1, i + 1).reduce((acc, item) => acc + item.close, 0);
      const average = sum / period;
      
      result.push({
        time: (new Date(data[i].time).getTime() / 1000) as UTCTimestamp,
        value: average,
      });
    }
    
    return result;
  };

  const calculateEMA = (data: CustomCandlestickData[], period: number): LineData[] => {
    const result: LineData[] = [];
    const multiplier = 2 / (period + 1);
    
    // Start with SMA
    let ema = data.slice(0, period).reduce((acc, item) => acc + item.close, 0) / period;
    
    result.push({
      time: (new Date(data[period - 1].time).getTime() / 1000) as UTCTimestamp,
      value: ema,
    });
    
    for (let i = period; i < data.length; i++) {
      ema = (data[i].close - ema) * multiplier + ema;
      result.push({
        time: (new Date(data[i].time).getTime() / 1000) as UTCTimestamp,
        value: ema,
      });
    }
    
    return result;
  };

  const calculateRSI = (data: CustomCandlestickData[], period: number): LineData[] => {
    const result: LineData[] = [];
    const gains: number[] = [];
    const losses: number[] = [];
    
    for (let i = 1; i < data.length; i++) {
      const change = data[i].close - data[i - 1].close;
      gains.push(change > 0 ? change : 0);
      losses.push(change < 0 ? -change : 0);
    }
    
    for (let i = period; i <= gains.length; i++) {
      const avgGain = gains.slice(i - period, i).reduce((a, b) => a + b, 0) / period;
      const avgLoss = losses.slice(i - period, i).reduce((a, b) => a + b, 0) / period;
      
      const rs = avgGain / avgLoss;
      const rsi = 100 - (100 / (1 + rs));
      
      result.push({
        time: (new Date(data[i].time).getTime() / 1000) as UTCTimestamp,
        value: rsi,
      });
    }
    
    return result;
  };

  const calculateMACD = (data: CustomCandlestickData[]): LineData[] => {
    const ema12 = calculateEMA(data, 12);
    const ema26 = calculateEMA(data, 26);
    const result: LineData[] = [];
    
    const startIndex = Math.max(0, ema26.length - ema12.length);
    
    for (let i = 0; i < ema12.length - startIndex; i++) {
      const macd = ema12[i + startIndex].value - ema26[i].value;
      result.push({
        time: ema12[i + startIndex].time,
        value: macd,
      });
    }
    
    return result;
  };

  const getIndicatorColor = (indicatorId: string): string => {
    const colors: Record<string, string> = {
      sma20: '#2196F3',
      sma50: '#FF9800',
      ema20: '#9C27B0',
      rsi: '#4CAF50',
      macd: '#F44336',
    };
    return colors[indicatorId] || '#666666';
  };

  // Toggle indicator
  const toggleIndicator = useCallback((indicatorId: string) => {
    setIndicators(prev => prev.map(indicator => {
      if (indicator.id === indicatorId) {
        const updated = { ...indicator, visible: !indicator.visible };
        
        if (!updated.visible && updated.series && chartRef.current) {
          chartRef.current.removeSeries(updated.series);
          updated.series = undefined;
        }
        
        return updated;
      }
      return indicator;
    }));
  }, []);

  // Handle real-time updates
  useEffect(() => {
    const quote = quotes[symbol];
    if (quote && candlestickSeriesRef.current) {
      // Update the last candlestick with real-time data
      const timestamp = (new Date(quote.timestamp).getTime() / 1000) as UTCTimestamp;
      
      candlestickSeriesRef.current.update({
        time: timestamp,
        open: quote.price, // This would need to be tracked properly
        high: quote.price,
        low: quote.price,
        close: quote.price,
      });
    }
  }, [quotes, symbol]);

  // Load data when symbol or timeframe changes
  useEffect(() => {
    loadHistoricalData();
  }, [loadHistoricalData]);

  // Subscribe to real-time updates
  useEffect(() => {
    if (webSocket.isConnected) {
      webSocket.subscribeToSymbols([symbol]);
    }

    return () => {
      if (webSocket.isConnected) {
        webSocket.unsubscribeFromSymbols([symbol]);
      }
    };
  }, [webSocket.isConnected, symbol, webSocket]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Toolbar */}
      {showToolbar && (
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-600">
          <div className="flex items-center space-x-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {symbol}
            </h3>
            
            {/* Timeframe Selector */}
            <div className="flex space-x-1">
              {['1m', '5m', '15m', '1h', '4h', '1d', '1w'].map((timeframe) => (
                <button
                  key={timeframe}
                  onClick={() => setChartConfig(prev => ({ ...prev, timeframe: timeframe as any }))}
                  className={`px-2 py-1 text-xs rounded ${
                    chartConfig.timeframe === timeframe
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {timeframe}
                </button>
              ))}
            </div>
          </div>

          {/* Indicators */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 dark:text-gray-300">Indicators:</span>
            {indicators.map((indicator) => (
              <button
                key={indicator.id}
                onClick={() => toggleIndicator(indicator.id)}
                className={`px-2 py-1 text-xs rounded ${
                  indicator.visible
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {indicator.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chart Container */}
      <div className="flex-1 relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-600">Loading chart data...</p>
            </div>
          </div>
        )}
        
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75 z-10">
            <div className="text-center">
              <p className="text-red-600">{error}</p>
              <button
                onClick={loadHistoricalData}
                className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              >
                Retry
              </button>
            </div>
          </div>
        )}
        
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>
    </div>
  );
};

export default TradingChart;