import { ApiClient } from '../api'

// Helper function to create mock Response objects
function createMockResponse(options: {
  ok?: boolean
  status?: number
  statusText?: string
  json?: () => Promise<any>
  text?: () => Promise<string>
}): Response {
  return {
    ok: options.ok ?? true,
    status: options.status ?? 200,
    statusText: options.statusText ?? 'OK',
    headers: new Headers(),
    redirected: false,
    type: 'basic',
    url: 'http://localhost:8000/api/v1/test',
    clone: jest.fn(),
    body: null,
    bodyUsed: false,
    arrayBuffer: jest.fn(),
    blob: jest.fn(),
    formData: jest.fn(),
    text: options.text ?? jest.fn(),
    json: options.json ?? jest.fn(),
    bytes: jest.fn(),
  } as Response
}

describe('ApiClient', () => {
  let apiClient: ApiClient
  let mockFetch: jest.MockedFunction<typeof fetch>

  beforeEach(() => {
    apiClient = new ApiClient()
    mockFetch = fetch as jest.MockedFunction<typeof fetch>
    jest.clearAllMocks()
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })

  describe('constructor', () => {
    it('should initialize with default base URL', () => {
      expect(apiClient['baseURL']).toBe('http://localhost:8000')
    })

    it('should use environment variable for base URL', () => {
      const originalEnv = process.env.NEXT_PUBLIC_API_URL
      process.env.NEXT_PUBLIC_API_URL = 'https://api.trading.com'
      
      const client = new ApiClient()
      expect(client['baseURL']).toBe('https://api.trading.com')
      
      process.env.NEXT_PUBLIC_API_URL = originalEnv
    })

    it('should set default headers', () => {
      expect(apiClient['defaultHeaders']['Content-Type']).toBe('application/json')
    })
  })

  describe('authentication', () => {
    it('should set auth token', () => {
      const token = 'test-token-123'
      apiClient.setAuthToken(token)
      
      expect(apiClient['defaultHeaders']['Authorization']).toBe(`Bearer ${token}`)
    })

    it('should clear auth token', () => {
      apiClient.setAuthToken('test-token')
      apiClient.clearAuthToken()
      
      expect(apiClient['defaultHeaders']['Authorization']).toBeUndefined()
    })
  })

  describe('buildURL', () => {
    it('should build URL without parameters', () => {
      const url = apiClient['buildURL']('/test')
      expect(url).toBe('http://localhost:8000/api/v1/test')
    })

    it('should build URL with query parameters', () => {
      const url = apiClient['buildURL']('/test', { 
        param1: 'value1', 
        param2: 'value2' 
      })
      expect(url).toBe('http://localhost:8000/api/v1/test?param1=value1&param2=value2')
    })

    it('should handle array parameters', () => {
      const url = apiClient['buildURL']('/test', { 
        symbols: ['AAPL', 'GOOGL', 'MSFT'] 
      })
      expect(url).toBe('http://localhost:8000/api/v1/test?symbols=AAPL&symbols=GOOGL&symbols=MSFT')
    })

    it('should skip null and undefined parameters', () => {
      const url = apiClient['buildURL']('/test', { 
        param1: 'value1',
        param2: null,
        param3: undefined,
        param4: 'value4'
      })
      expect(url).toBe('http://localhost:8000/api/v1/test?param1=value1&param4=value4')
    })
  })

  describe('HTTP methods', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue(createMockResponse({
        json: async () => ({ success: true, data: 'test data', message: 'success' })
      }))
    })

    describe('GET requests', () => {
      it('should make GET request successfully', async () => {
        const response = await apiClient.get('/test')

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/test',
          expect.objectContaining({
            method: 'GET',
            headers: expect.objectContaining({
              'Content-Type': 'application/json'
            }),
            credentials: 'include'
          })
        )
        expect(response.success).toBe(true)
        expect(response.data).toBe('test data')
      })

      it('should include query parameters in GET request', async () => {
        await apiClient.get('/test', { 
          params: { symbol: 'AAPL', exchange: 'NSE' } 
        })

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/test?symbol=AAPL&exchange=NSE',
          expect.any(Object)
        )
      })

      it('should include custom headers', async () => {
        await apiClient.get('/test', { 
          headers: { 'X-Custom-Header': 'custom-value' } 
        })

        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-Custom-Header': 'custom-value'
            })
          })
        )
      })
    })

    describe('POST requests', () => {
      it('should make POST request with JSON body', async () => {
        const testData = { symbol: 'AAPL', quantity: 100 }
        await apiClient.post('/test', testData)

        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1/test',
          expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({
              'Content-Type': 'application/json'
            }),
            body: JSON.stringify(testData),
            credentials: 'include'
          })
        )
      })

      it('should make POST request without body', async () => {
        await apiClient.post('/test')

        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            method: 'POST',
            body: undefined
          })
        )
      })
    })

    describe('PUT requests', () => {
      it('should make PUT request with JSON body', async () => {
        const testData = { id: 1, name: 'test' }
        await apiClient.put('/test', testData)

        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            method: 'PUT',
            body: JSON.stringify(testData)
          })
        )
      })
    })

    describe('PATCH requests', () => {
      it('should make PATCH request with JSON body', async () => {
        const testData = { name: 'updated name' }
        await apiClient.patch('/test', testData)

        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            method: 'PATCH',
            body: JSON.stringify(testData)
          })
        )
      })
    })

    describe('DELETE requests', () => {
      it('should make DELETE request', async () => {
        await apiClient.delete('/test')

        expect(mockFetch).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            method: 'DELETE',
            body: undefined
          })
        )
      })
    })
  })

  describe('error handling', () => {
    it('should handle HTTP error responses', async () => {
      mockFetch.mockResolvedValue(createMockResponse({
        ok: false,
        status: 404,
        text: async () => 'Not Found'
      }))

      const response = await apiClient.get('/nonexistent')

      expect(response.success).toBe(false)
      expect(response.error).toContain('HTTP 404')
    })

    it('should handle 401 unauthorized responses', async () => {
      mockFetch.mockResolvedValue(createMockResponse({
        ok: false,
        status: 401,
        text: async () => 'Unauthorized'
      }))

      // Mock window.location for browser environment test
      const mockLocation = { href: '' }
      Object.defineProperty(window, 'location', {
        value: mockLocation,
        writable: true
      })

      const response = await apiClient.get('/protected')

      expect(response.success).toBe(false)
      // Should clear auth token on 401
      expect(apiClient['defaultHeaders']['Authorization']).toBeUndefined()
    })

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValue(new Error('Network error'))

      const response = await apiClient.get('/test')

      expect(response.success).toBe(false)
      expect(response.error).toBe('Network error')
    })

    it('should handle timeout', async () => {
      // Mock a timeout scenario
      jest.useFakeTimers()
      
      mockFetch.mockImplementation(() => {
        return new Promise(() => {
          // Promise that never resolves (simulates timeout)
        })
      })

      const requestPromise = apiClient.get('/test', { timeout: 1000 })
      
      // Fast-forward time
      jest.advanceTimersByTime(1100)
      
      const response = await requestPromise
      
      expect(response.success).toBe(false)
      
      jest.useRealTimers()
    }, 10000) // Increase timeout for this test
  })

  describe('file upload', () => {
    it('should upload file successfully', async () => {
      mockFetch.mockResolvedValue(createMockResponse({
        json: async () => ({ success: true, data: { fileId: 'file123' }, message: 'File uploaded' })
      }))

      const mockFile = new File(['content'], 'test.txt', { type: 'text/plain' })
      const additionalData = { category: 'documents' }

      const response = await apiClient.uploadFile('/upload', mockFile, additionalData)

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/upload',
        expect.objectContaining({
          method: 'POST',
          body: expect.any(FormData),
          credentials: 'include'
        })
      )
      expect(response.success).toBe(true)
    })

    it('should handle file upload errors', async () => {
      mockFetch.mockResolvedValue(createMockResponse({
        ok: false,
        status: 413,
        statusText: 'Payload Too Large'
      }))

      const mockFile = new File(['content'], 'large-file.txt')
      const response = await apiClient.uploadFile('/upload', mockFile)

      expect(response.success).toBe(false)
      expect(response.error).toContain('HTTP 413')
    })
  })

  describe('health check', () => {
    it('should perform health check successfully', async () => {
      mockFetch.mockResolvedValue(createMockResponse({
        json: async () => ({ success: true })
      }))

      const isHealthy = await apiClient.healthCheck()

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/health',
        expect.any(Object)
      )
      expect(isHealthy).toBe(true)
    })

    it('should return false on health check failure', async () => {
      mockFetch.mockRejectedValue(new Error('Service unavailable'))

      const isHealthy = await apiClient.healthCheck()

      expect(isHealthy).toBe(false)
    })
  })

  describe('request configuration', () => {
    it('should respect custom timeout', async () => {
      jest.useFakeTimers()
      
      mockFetch.mockImplementation(() => new Promise(() => {}))

      const requestPromise = apiClient.get('/test', { timeout: 5000 })
      
      jest.advanceTimersByTime(5100)
      
      const response = await requestPromise
      expect(response.success).toBe(false)
      
      jest.useRealTimers()
    }, 10000)

    it('should use default timeout when not specified', async () => {
      jest.useFakeTimers()
      
      mockFetch.mockImplementation(() => new Promise(() => {}))

      const requestPromise = apiClient.get('/test')
      
      // Default timeout is 30000ms
      jest.advanceTimersByTime(30100)
      
      const response = await requestPromise
      expect(response.success).toBe(false)
      
      jest.useRealTimers()
    }, 40000)
  })

  describe('response parsing', () => {
    it('should parse JSON response correctly', async () => {
      const mockData = { users: [{ id: 1, name: 'John' }] }
      mockFetch.mockResolvedValue(createMockResponse({
        json: async () => ({ success: true, data: mockData })
      }))

      const response = await apiClient.get('/users')

      expect(response.data).toEqual(mockData)
    })

    it('should handle malformed JSON response', async () => {
      mockFetch.mockResolvedValue(createMockResponse({
        json: async () => { throw new Error('Invalid JSON') }
      }))

      const response = await apiClient.get('/test')

      expect(response.success).toBe(false)
      expect(response.error).toContain('Invalid JSON')
    })
  })
})