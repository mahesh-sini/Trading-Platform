import React, { useState, useEffect } from 'react';
import { Layout } from '@/components/layout/Layout';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { 
  CpuChipIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

const AIInsights: React.FC = () => {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modelMetrics, setModelMetrics] = useState({
    accuracy: 0,
    sharpeRatio: 0,
    totalPredictions: 0,
    successfulTrades: 0
  });

  // Fetch real predictions and metrics on component mount
  useEffect(() => {
    fetchAIInsights();
  }, []);

  const fetchAIInsights = async () => {
    try {
      setLoading(true);
      
      // Fetch latest predictions from backend API
      const predictionsResponse = await fetch('/api/predictions');
      if (predictionsResponse.ok) {
        const predictionsData = await predictionsResponse.json();
        setPredictions(predictionsData.predictions || []);
      }
      
      // Fetch model performance metrics
      const metricsResponse = await fetch('/api/predictions/performance');
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setModelMetrics({
          accuracy: metricsData.accuracy || 0,
          sharpeRatio: metricsData.sharpe_ratio || 0,
          totalPredictions: metricsData.total_predictions || 0,
          successfulTrades: metricsData.successful_trades || 0
        });
      }
      
    } catch (error) {
      console.error('Failed to fetch AI insights:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateNewPrediction = async (symbol: string) => {
    try {
      const response = await fetch('/api/predictions/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          symbol: symbol,
          timeframe: 'intraday',
          horizon: '1d'
        })
      });
      
      if (response.ok) {
        const newPrediction = await response.json();
        setPredictions(prev => [newPrediction, ...prev.slice(0, 9)]);
      }
    } catch (error) {
      console.error('Failed to generate prediction:', error);
    }
  };

  const startModelTraining = async () => {
    try {
      const response = await fetch('http://localhost:8001/v1/models/train', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          symbol: 'RELIANCE',
          timeframe: 'intraday',
          model_type: 'random_forest',
          training_data_days: 365
        })
      });
      
      if (response.ok) {
        alert('Model training started successfully!');
      }
    } catch (error) {
      console.error('Failed to start training:', error);
      alert('Failed to start model training');
    }
  };

  const runBacktest = async () => {
    try {
      // Call ML service for backtesting
      alert('Backtesting feature coming soon!');
    } catch (error) {
      console.error('Failed to run backtest:', error);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">AI Insights</h1>
          <p className="text-gray-600">Machine learning powered trading predictions and insights</p>
        </div>

        {/* Model Performance */}
        <Card>
          <CardHeader title="Model Performance" subtitle="Real-time ML model analytics" />
          <CardBody>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{modelMetrics.accuracy}%</div>
                <div className="text-sm text-gray-600">Prediction Accuracy</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">{modelMetrics.sharpeRatio}</div>
                <div className="text-sm text-gray-600">Sharpe Ratio</div>
              </div>
              <div className="text-center p-4 bg-purple-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">{modelMetrics.totalPredictions}</div>
                <div className="text-sm text-gray-600">Total Predictions</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">{modelMetrics.successfulTrades}</div>
                <div className="text-sm text-gray-600">Successful Trades</div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* AI Predictions */}
        <Card>
          <CardHeader title="Latest AI Predictions" subtitle="Real-time ML predictions for Indian stocks" />
          <CardBody>
            <div className="space-y-4">
              {loading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-2 text-gray-600">Loading AI predictions...</p>
                </div>
              ) : predictions.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-600">No predictions available. Generate new predictions below.</p>
                  <div className="mt-4 space-x-2">
                    <button
                      onClick={() => generateNewPrediction('RELIANCE')}
                      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Generate RELIANCE Prediction
                    </button>
                    <button
                      onClick={() => generateNewPrediction('TCS')}
                      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      Generate TCS Prediction
                    </button>
                  </div>
                </div>
              ) : (
                predictions.map((pred, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="font-bold text-lg text-gray-900">{pred.symbol}</div>
                      <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                        pred.prediction === 'BULLISH' ? 'bg-green-100 text-green-800' :
                        pred.prediction === 'BEARISH' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {pred.prediction}
                      </div>
                      <div className="text-sm text-gray-600">
                        Confidence: {pred.confidence}%
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-gray-900">Target: ₹{pred.target}</div>
                      <div className="text-sm text-gray-600">{pred.timeframe}</div>
                    </div>
                  </div>
                  <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded">
                    <strong>Reasoning:</strong> {pred.reasoning}
                  </div>
                </div>
              )))
              )}
            </div>
          </CardBody>
        </Card>

        {/* Model Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader title="Model Training" subtitle="Retrain models with latest data" />
            <CardBody>
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  Last training: 2 hours ago
                </div>
                <Button 
                  variant="primary" 
                  className="w-full"
                  onClick={startModelTraining}
                >
                  <CpuChipIcon className="w-5 h-5 mr-2" />
                  Start New Training
                </Button>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Backtesting" subtitle="Test strategies on historical data" />
            <CardBody>
              <div className="space-y-4">
                <div className="text-sm text-gray-600">
                  Last backtest: 1 day ago
                </div>
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={runBacktest}
                >
                  <ChartBarIcon className="w-5 h-5 mr-2" />
                  Run Backtest
                </Button>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default AIInsights;