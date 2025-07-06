import { marketDataService, formatPrice, formatChange, getChangeColor } from '../marketDataService'
import { ApiClient } from '../api'

// Mock the API client
jest.mock('../api')
const MockedApiClient = ApiClient as jest.MockedClass<typeof ApiClient>

describe('MarketDataService', () => {
  let mockApiInstance: jest.Mocked<ApiClient>

  beforeEach(() => {
    jest.clearAllMocks()
    mockApiInstance = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
      uploadFile: jest.fn(),
      healthCheck: jest.fn(),
      setAuthToken: jest.fn(),
      clearAuthToken: jest.fn(),
    } as any

    MockedApiClient.mockImplementation(() => mockApiInstance)
    
    // Reset the service instance
    marketDataService.stopAllStreams()
  })

  afterEach(() => {
    marketDataService.stopAllStreams()
  })

  describe('getLiveQuote', () => {
    it('should fetch live quote successfully', async () => {
      const mockQuote = {
        symbol: 'RELIANCE',
        price: 2500.75,
        change: 25.50,
        change_percent: 1.03,
        volume: 1500000,
        high: 2510.00,
        low: 2470.00,
        open: 2480.25,
        previous_close: 2475.25,
        bid: 2500.50,
        ask: 2501.00,
        timestamp: '2024-01-01T12:00:00Z',
        exchange: 'NSE',
        currency: 'INR'
      }

      mockApiInstance.get.mockResolvedValueOnce({
        success: true,
        data: mockQuote,
        message: 'Live quote for RELIANCE'
      })

      const result = await marketDataService.getLiveQuote('RELIANCE', 'NSE')

      expect(mockApiInstance.get).toHaveBeenCalledWith('/market/quote/RELIANCE', {
        params: { exchange: 'NSE' }
      })
      expect(result).toEqual(mockQuote)
    })

    it('should return null when API returns unsuccessful response', async () => {
      mockApiInstance.get.mockResolvedValueOnce({
        success: false,
        data: null,
        message: 'Quote not found',
        error: 'Symbol not found'
      })

      const result = await marketDataService.getLiveQuote('INVALID')

      expect(result).toBeNull()
    })

    it('should handle API errors gracefully', async () => {
      mockApiInstance.get.mockRejectedValueOnce(new Error('Network error'))

      const result = await marketDataService.getLiveQuote('RELIANCE')

      expect(result).toBeNull()
    })

    it('should use default exchange if not specified', async () => {
      mockApiInstance.get.mockResolvedValueOnce({
        success: true,
        data: { symbol: 'RELIANCE', price: 2500.75 },
        message: 'Success'
      })

      await marketDataService.getLiveQuote('RELIANCE')

      expect(mockApiInstance.get).toHaveBeenCalledWith('/market/quote/RELIANCE', {
        params: { exchange: 'NSE' }
      })
    })
  })

  describe('getBatchQuotes', () => {
    it('should fetch batch quotes successfully', async () => {
      const mockBatchResponse = {
        quotes: {
          'RELIANCE': { symbol: 'RELIANCE', price: 2500.75, change: 25.50 },
          'TCS': { symbol: 'TCS', price: 3500.25, change: -50.25 }
        },
        symbols_requested: ['RELIANCE', 'TCS', 'INFY'],
        symbols_found: ['RELIANCE', 'TCS'],
        errors: ['No data found for INFY']
      }

      mockApiInstance.get.mockResolvedValueOnce({
        success: true,
        data: mockBatchResponse,
        message: 'Batch quotes'
      })

      const result = await marketDataService.getBatchQuotes(['RELIANCE', 'TCS', 'INFY'])

      expect(mockApiInstance.get).toHaveBeenCalledWith('/market/quotes/batch', {
        params: { 
          symbols: ['RELIANCE', 'TCS', 'INFY'],
          exchange: 'NSE' 
        }
      })
      expect(result).toEqual(mockBatchResponse)
    })

    it('should return empty result on API failure', async () => {
      mockApiInstance.get.mockRejectedValueOnce(new Error('API error'))

      const result = await marketDataService.getBatchQuotes(['RELIANCE'])

      expect(result.quotes).toEqual({})
      expect(result.symbols_requested).toEqual(['RELIANCE'])
      expect(result.symbols_found).toEqual([])
      expect(result.errors.length).toBeGreaterThan(0)
    })
  })

  describe('getIndices', () => {
    it('should fetch Indian market indices successfully', async () => {
      const mockIndices = [
        { symbol: 'NIFTY', price: 19674.25, change: 156.80, changePercent: 0.80, data_source: 'live' },
        { symbol: 'SENSEX', price: 65930.77, change: 442.65, changePercent: 0.68, data_source: 'live' },
        { symbol: 'BANKNIFTY', price: 43567.90, change: -234.50, changePercent: -0.53, data_source: 'fallback' }
      ]

      mockApiInstance.get.mockResolvedValueOnce({
        success: true,
        data: mockIndices,
        message: 'Indian market indices'
      })

      const result = await marketDataService.getIndices()

      expect(mockApiInstance.get).toHaveBeenCalledWith('/market/indices')
      expect(result).toEqual(mockIndices)
      expect(result.length).toBe(3)
      expect(result[0].symbol).toBe('NIFTY')
    })

    it('should return fallback data on API failure', async () => {
      mockApiInstance.get.mockRejectedValueOnce(new Error('API error'))

      const result = await marketDataService.getIndices()

      expect(result.length).toBe(3)
      expect(result[0].symbol).toBe('NIFTY')
      expect(result[0].data_source).toBe('fallback')
    })
  })

  describe('getHistoricalData', () => {
    it('should fetch historical data successfully', async () => {
      const mockHistoricalBars = [
        {
          timestamp: '2024-01-01T09:15:00Z',
          open: 2480.25,
          high: 2510.00,
          low: 2470.00,
          close: 2500.75,
          volume: 1500000
        },
        {
          timestamp: '2024-01-01T09:16:00Z',
          open: 2500.75,
          high: 2515.50,
          low: 2495.00,
          close: 2510.25,
          volume: 1200000
        }
      ]

      mockApiInstance.get.mockResolvedValueOnce({
        success: true,
        data: { bars: mockHistoricalBars },
        message: 'Historical data'
      })

      const result = await marketDataService.getHistoricalData('RELIANCE', '1d', '1m')

      expect(mockApiInstance.get).toHaveBeenCalledWith('/market/historical/RELIANCE', {
        params: { period: '1d', interval: '1m', exchange: 'NSE' }
      })
      expect(result).toEqual(mockHistoricalBars)
      expect(result.length).toBe(2)
    })

    it('should return empty array on API failure', async () => {
      mockApiInstance.get.mockRejectedValueOnce(new Error('API error'))

      const result = await marketDataService.getHistoricalData('RELIANCE')

      expect(result).toEqual([])
    })
  })

  describe('getMarketMovers', () => {
    it('should fetch market movers successfully', async () => {
      const mockMovers = {
        top_gainers: [
          { symbol: 'ADANIGREEN', price: 1245.60, change: 8.5, changePercent: 8.5 },
          { symbol: 'TATAMOTORS', price: 567.80, change: 6.2, changePercent: 6.2 }
        ],
        top_losers: [
          { symbol: 'ZEEL', price: 234.50, change: -5.2, changePercent: -5.2 },
          { symbol: 'YESBANK', price: 18.65, change: -3.8, changePercent: -3.8 }
        ]
      }

      mockApiInstance.get.mockResolvedValueOnce({
        success: true,
        data: mockMovers,
        message: 'Market movers'
      })

      const result = await marketDataService.getMarketMovers()

      expect(mockApiInstance.get).toHaveBeenCalledWith('/market/market-movers')
      expect(result).toEqual(mockMovers)
      expect(result.top_gainers.length).toBe(2)
      expect(result.top_losers.length).toBe(2)
    })

    it('should return fallback data on API failure', async () => {
      mockApiInstance.get.mockRejectedValueOnce(new Error('API error'))

      const result = await marketDataService.getMarketMovers()

      expect(result.top_gainers.length).toBeGreaterThan(0)
      expect(result.top_losers.length).toBeGreaterThan(0)
    })
  })

  describe('subscribeToRealTime', () => {
    it('should subscribe to real-time updates successfully', async () => {
      mockApiInstance.post.mockResolvedValueOnce({
        success: true,
        data: { subscribed_symbols: ['RELIANCE', 'TCS'] },
        message: 'Subscribed'
      })

      const result = await marketDataService.subscribeToRealTime(['RELIANCE', 'TCS'])

      expect(mockApiInstance.post).toHaveBeenCalledWith('/market/subscribe', {
        symbols: ['RELIANCE', 'TCS']
      })
      expect(result).toBe(true)
    })

    it('should return false on API failure', async () => {
      mockApiInstance.post.mockRejectedValueOnce(new Error('API error'))

      const result = await marketDataService.subscribeToRealTime(['RELIANCE'])

      expect(result).toBe(false)
    })
  })

  describe('real-time streaming', () => {
    let mockEventSource: jest.Mocked<EventSource>

    beforeEach(() => {
      mockEventSource = {
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        close: jest.fn(),
        dispatchEvent: jest.fn(),
        onerror: null,
        onmessage: null,
        onopen: null,
        readyState: EventSource.CONNECTING,
        url: '',
        withCredentials: false,
        CONNECTING: EventSource.CONNECTING,
        OPEN: EventSource.OPEN,
        CLOSED: EventSource.CLOSED
      }

      // Mock EventSource constructor
      global.EventSource = jest.fn(() => mockEventSource) as any
    })

    afterEach(() => {
      jest.restoreAllMocks()
    })

    it('should start streaming for a symbol', () => {
      const mockHandler = jest.fn()
      
      marketDataService.startStream('RELIANCE', mockHandler)

      expect(global.EventSource).toHaveBeenCalledWith(
        expect.stringContaining('/market/stream/RELIANCE'),
        { withCredentials: true }
      )
    })

    it('should handle stream messages', () => {
      const mockHandler = jest.fn()
      const testData = {
        type: 'quote_update',
        symbol: 'RELIANCE',
        data: { price: 2500.75 },
        timestamp: '2024-01-01T12:00:00Z'
      }

      marketDataService.startStream('RELIANCE', mockHandler)

      // Simulate receiving a message
      if (mockEventSource.onmessage) {
        const event = { data: JSON.stringify(testData) } as MessageEvent
        mockEventSource.onmessage(event)
      }

      expect(mockHandler).toHaveBeenCalledWith(testData)
    })

    it('should stop streaming for a symbol', () => {
      const mockHandler = jest.fn()
      
      marketDataService.startStream('RELIANCE', mockHandler)
      marketDataService.stopStream('RELIANCE')

      expect(mockEventSource.close).toHaveBeenCalled()
    })

    it('should stop all active streams', () => {
      const mockHandler = jest.fn()
      
      marketDataService.startStream('RELIANCE', mockHandler)
      marketDataService.startStream('TCS', mockHandler)
      marketDataService.stopAllStreams()

      expect(mockEventSource.close).toHaveBeenCalledTimes(2)
    })
  })

  describe('checkHealth', () => {
    it('should return true when service is healthy', async () => {
      mockApiInstance.get.mockResolvedValueOnce({
        success: true,
        data: { service_status: 'healthy' },
        message: 'Service healthy'
      })

      const result = await marketDataService.checkHealth()

      expect(mockApiInstance.get).toHaveBeenCalledWith('/market/health')
      expect(result).toBe(true)
    })

    it('should return false when service is unhealthy', async () => {
      mockApiInstance.get.mockResolvedValueOnce({
        success: false,
        data: { service_status: 'unhealthy' },
        message: 'Service unhealthy'
      })

      const result = await marketDataService.checkHealth()

      expect(result).toBe(false)
    })

    it('should return false on API error', async () => {
      mockApiInstance.get.mockRejectedValueOnce(new Error('Network error'))

      const result = await marketDataService.checkHealth()

      expect(result).toBe(false)
    })
  })
})

describe('Utility Functions', () => {
  describe('formatPrice', () => {
    it('should format INR prices correctly', () => {
      expect(formatPrice(2500.75, 'INR')).toBe('₹2,500.75')
      expect(formatPrice(1234567.89, 'INR')).toBe('₹12,34,567.89')
      expect(formatPrice(0.50, 'INR')).toBe('₹0.50')
    })

    it('should format USD prices correctly', () => {
      expect(formatPrice(150.25, 'USD')).toBe('150.25')
      expect(formatPrice(1234.56, 'USD')).toBe('1,234.56')
    })

    it('should default to INR formatting', () => {
      expect(formatPrice(2500.75)).toBe('₹2,500.75')
    })
  })

  describe('formatChange', () => {
    it('should format positive changes correctly', () => {
      expect(formatChange(25.50, 1.03)).toBe('+25.50 (+1.03%)')
      expect(formatChange(0.15, 0.01)).toBe('+0.15 (+0.01%)')
    })

    it('should format negative changes correctly', () => {
      expect(formatChange(-25.50, -1.03)).toBe('-25.50 (-1.03%)')
      expect(formatChange(-0.15, -0.01)).toBe('-0.15 (-0.01%)')
    })

    it('should format zero change correctly', () => {
      expect(formatChange(0, 0)).toBe('0.00 (0.00%)')
    })
  })

  describe('getChangeColor', () => {
    it('should return green color for positive changes', () => {
      expect(getChangeColor(25.50)).toBe('text-green-600')
      expect(getChangeColor(0.01)).toBe('text-green-600')
    })

    it('should return red color for negative changes', () => {
      expect(getChangeColor(-25.50)).toBe('text-red-600')
      expect(getChangeColor(-0.01)).toBe('text-red-600')
    })

    it('should return green color for zero change', () => {
      expect(getChangeColor(0)).toBe('text-green-600')
    })
  })
})