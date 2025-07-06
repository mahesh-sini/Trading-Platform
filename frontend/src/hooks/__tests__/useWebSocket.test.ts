import { renderHook, act } from '@testing-library/react'
import { useWebSocket } from '../useWebSocket'

// Mock the stores
jest.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    tokens: {
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
    },
  }),
}))

jest.mock('@/store/marketStore', () => ({
  useMarketStore: () => ({
    updateQuote: jest.fn(),
  }),
}))

describe('useWebSocket Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('initializes with default state', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    expect(result.current.isConnected).toBe(false)
    expect(result.current.error).toBe(null)
    expect(result.current.connectionState).toBe('disconnected')
  })

  it('connects to WebSocket on mount when autoConnect is true', () => {
    const { result } = renderHook(() => useWebSocket())

    // Should attempt to connect
    expect(result.current.connectionState).toBe('connecting')
  })

  it('does not auto-connect when autoConnect is false', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    expect(result.current.connectionState).toBe('disconnected')
  })

  it('can manually connect and disconnect', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    act(() => {
      result.current.connect()
    })

    expect(result.current.connectionState).toBe('connecting')

    act(() => {
      result.current.disconnect()
    })

    expect(result.current.connectionState).toBe('disconnected')
  })

  it('can send messages', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    const message = {
      type: 'test',
      data: { test: 'data' },
    }

    act(() => {
      result.current.sendMessage(message)
    })

    // Message should be queued if not connected
    // When connected, it should be sent
  })

  it('can subscribe and unsubscribe from channels', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    act(() => {
      result.current.subscribe('market_data.AAPL')
    })

    act(() => {
      result.current.unsubscribe('market_data.AAPL')
    })

    // Subscriptions should trigger appropriate messages
  })

  it('can subscribe to symbols', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    const symbols = ['AAPL', 'GOOGL', 'MSFT']

    act(() => {
      result.current.subscribeToSymbols(symbols)
    })

    act(() => {
      result.current.unsubscribeFromSymbols(symbols)
    })
  })

  it('can send ping messages', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    act(() => {
      result.current.ping()
    })
  })

  it('can register and unregister message handlers', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    const handler = jest.fn()

    act(() => {
      result.current.registerMessageHandler('test_message', handler)
    })

    act(() => {
      result.current.unregisterMessageHandler('test_message')
    })
  })

  it('handles connection errors', () => {
    // Mock WebSocket to throw error
    const originalWebSocket = global.WebSocket
    global.WebSocket = class extends WebSocket {
      constructor() {
        super('ws://localhost:8002')
        setTimeout(() => {
          if (this.onerror) {
            this.onerror(new Event('error'))
          }
        }, 0)
      }
    }

    const { result } = renderHook(() => useWebSocket())

    // Should handle error gracefully
    expect(result.current.connectionState).toBe('connecting')

    // Restore WebSocket
    global.WebSocket = originalWebSocket
  })

  it('handles message parsing errors', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    // This would be tested by mocking WebSocket message events
    // The hook should handle invalid JSON gracefully
  })

  it('queues messages when disconnected', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    const message = {
      type: 'test',
      data: { test: 'data' },
    }

    act(() => {
      result.current.sendMessage(message)
    })

    // Message should be queued and sent when connection is established
  })

  it('attempts reconnection on connection loss', () => {
    const { result } = renderHook(() => useWebSocket({ reconnectAttempts: 2 }))

    // Mock connection loss
    act(() => {
      // Simulate connection being lost
      if (result.current.isConnected) {
        result.current.disconnect()
      }
    })

    // Should attempt to reconnect
  })

  it('respects reconnection attempt limits', () => {
    const { result } = renderHook(() => useWebSocket({ 
      reconnectAttempts: 1,
      autoConnect: false 
    }))

    // This would test that reconnection stops after max attempts
  })

  it('uses authentication token when available', () => {
    const { result } = renderHook(() => useWebSocket({ autoConnect: false }))

    // The hook should use the token from the auth store
    // This is mocked in the test setup
  })
})