/**
 * K6 Load Testing Script for Trading Platform
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 20 }, // Ramp up to 20 users
    { duration: '5m', target: 20 }, // Stay at 20 users
    { duration: '2m', target: 50 }, // Ramp up to 50 users
    { duration: '5m', target: 50 }, // Stay at 50 users
    { duration: '2m', target: 0 },  // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.05'],   // Error rate under 5%
    errors: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Test data
const symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'NVDA'];
const timeframes = ['1m', '5m', '15m', '1h', '1d'];

let authToken = null;
let userId = null;

export function setup() {
  // Setup phase - authenticate a test user
  const loginResponse = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
    email: 'loadtest@example.com',
    password: 'loadtestpassword123'
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginResponse.status === 200) {
    const responseData = JSON.parse(loginResponse.body);
    return {
      authToken: responseData.access_token,
      userId: responseData.user_id
    };
  }
  
  return { authToken: null, userId: null };
}

export default function(data) {
  if (data && data.authToken) {
    authToken = data.authToken;
    userId = data.userId;
  }

  const headers = authToken ? {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  } : {
    'Content-Type': 'application/json'
  };

  // Test 1: Get market data (most frequent operation)
  const symbol = symbols[Math.floor(Math.random() * symbols.length)];
  const quoteResponse = http.get(`${BASE_URL}/market/quote/${symbol}`, { headers });
  
  check(quoteResponse, {
    'market quote status is 200': (r) => r.status === 200,
    'market quote response time < 100ms': (r) => r.timings.duration < 100,
  }) || errorRate.add(1);

  sleep(0.5);

  // Test 2: Get historical data
  const timeframe = timeframes[Math.floor(Math.random() * timeframes.length)];
  const historyResponse = http.get(
    `${BASE_URL}/market/history/${symbol}?timeframe=${timeframe}&limit=100`,
    { headers }
  );
  
  check(historyResponse, {
    'history data status is 200': (r) => r.status === 200,
    'history data response time < 200ms': (r) => r.timings.duration < 200,
  }) || errorRate.add(1);

  sleep(0.5);

  // Test 3: Get portfolio (authenticated users only)
  if (authToken && userId) {
    const portfolioResponse = http.get(`${BASE_URL}/portfolio/${userId}`, { headers });
    
    check(portfolioResponse, {
      'portfolio status is 200': (r) => r.status === 200,
      'portfolio response time < 200ms': (r) => r.timings.duration < 200,
    }) || errorRate.add(1);

    sleep(0.5);

    // Test 4: Get positions
    const positionsResponse = http.get(`${BASE_URL}/positions/${userId}`, { headers });
    
    check(positionsResponse, {
      'positions status is 200': (r) => r.status === 200,
      'positions response time < 200ms': (r) => r.timings.duration < 200,
    }) || errorRate.add(1);

    sleep(0.5);

    // Test 5: Get orders
    const ordersResponse = http.get(`${BASE_URL}/orders/${userId}`, { headers });
    
    check(ordersResponse, {
      'orders status is 200': (r) => r.status === 200,
      'orders response time < 200ms': (r) => r.timings.duration < 200,
    }) || errorRate.add(1);
  }

  sleep(1);

  // Test 6: Get news
  const newsResponse = http.get(`${BASE_URL}/news?limit=20`, { headers });
  
  check(newsResponse, {
    'news status is 200': (r) => r.status === 200,
    'news response time < 300ms': (r) => r.timings.duration < 300,
  }) || errorRate.add(1);

  sleep(0.5);

  // Test 7: Technical indicators
  const indicator = ['sma', 'ema', 'rsi', 'macd'][Math.floor(Math.random() * 4)];
  const indicatorResponse = http.get(
    `${BASE_URL}/market/indicators/${symbol}/${indicator}`,
    { headers }
  );
  
  check(indicatorResponse, {
    'indicator status is 200': (r) => r.status === 200,
    'indicator response time < 150ms': (r) => r.timings.duration < 150,
  }) || errorRate.add(1);

  sleep(0.5);

  // Test 8: Symbol search
  const searchQueries = ['Apple', 'Tesla', 'Microsoft', 'Google'];
  const query = searchQueries[Math.floor(Math.random() * searchQueries.length)];
  const searchResponse = http.get(`${BASE_URL}/market/search?q=${query}`, { headers });
  
  check(searchResponse, {
    'search status is 200': (r) => r.status === 200,
    'search response time < 100ms': (r) => r.timings.duration < 100,
  }) || errorRate.add(1);

  // Simulate real user behavior with longer pause
  sleep(Math.random() * 3 + 1);
}

export function teardown(data) {
  // Cleanup phase
  console.log('Load test completed');
}