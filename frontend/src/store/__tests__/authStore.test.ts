import { useAuthStore } from '../authStore'
import { act, renderHook } from '@testing-library/react'
import { SubscriptionTier } from '../../types/index'

// Mock fetch
global.fetch = jest.fn()

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.getState().logout()
    jest.clearAllMocks()
  })

  afterEach(() => {
    jest.resetAllMocks()
  })

  it('initializes with default state', () => {
    const { result } = renderHook(() => useAuthStore())

    expect(result.current.user).toBe(null)
    expect(result.current.tokens).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('handles successful login', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      subscription_tier: SubscriptionTier.FREE,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    const mockTokens = {
      access_token: 'access_token',
      refresh_token: 'refresh_token',
      token_type: 'Bearer',
      expires_in: 3600,
    }

    const mockResponse = {
      user: mockUser,
      tokens: mockTokens,
    }

    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      await result.current.login('test@example.com', 'password')
    })

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.tokens).toEqual(mockTokens)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('handles login failure', async () => {
    const mockError = { message: 'Invalid credentials' }

    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => mockError,
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      try {
        await result.current.login('test@example.com', 'wrongpassword')
      } catch (error) {
        // Expected to throw
      }
    })

    expect(result.current.user).toBe(null)
    expect(result.current.tokens).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe('Invalid credentials')
  })

  it('handles successful registration', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      subscription_tier: SubscriptionTier.FREE,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    const mockTokens = {
      access_token: 'access_token',
      refresh_token: 'refresh_token',
      token_type: 'Bearer',
      expires_in: 3600,
    }

    const mockResponse = {
      user: mockUser,
      tokens: mockTokens,
    }

    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      await result.current.register('test@example.com', 'password', 'Test', 'User')
    })

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.tokens).toEqual(mockTokens)
    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('handles registration failure', async () => {
    const mockError = { message: 'Email already exists' }

    ;(global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: async () => mockError,
    })

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      try {
        await result.current.register('test@example.com', 'password', 'Test', 'User')
      } catch (error) {
        // Expected to throw
      }
    })

    expect(result.current.user).toBe(null)
    expect(result.current.tokens).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe('Email already exists')
  })

  it('handles logout', () => {
    const { result } = renderHook(() => useAuthStore())

    // Set some state first
    act(() => {
      result.current.setUser({
        id: '1',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        subscription_tier: SubscriptionTier.FREE,
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      })
      result.current.setTokens({
        access_token: 'access_token',
        refresh_token: 'refresh_token',
        token_type: 'Bearer',
        expires_in: 3600,
      })
    })

    expect(result.current.isAuthenticated).toBe(true)

    act(() => {
      result.current.logout()
    })

    expect(result.current.user).toBe(null)
    expect(result.current.tokens).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('sets loading state during async operations', async () => {
    ;(global.fetch as jest.Mock).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ ok: true, json: async () => ({}) }), 100)
        )
    )

    const { result } = renderHook(() => useAuthStore())

    act(() => {
      result.current.login('test@example.com', 'password')
    })

    expect(result.current.isLoading).toBe(true)

    // Wait for async operation to complete
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 150))
    })

    expect(result.current.isLoading).toBe(false)
  })

  it('can set and clear errors', () => {
    const { result } = renderHook(() => useAuthStore())

    act(() => {
      result.current.setError('Test error')
    })

    expect(result.current.error).toBe('Test error')

    act(() => {
      result.current.clearError()
    })

    expect(result.current.error).toBe(null)
  })

  it('can set user and tokens directly', () => {
    const { result } = renderHook(() => useAuthStore())

    const mockUser = {
      id: '1',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      subscription_tier: SubscriptionTier.FREE,
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    const mockTokens = {
      access_token: 'access_token',
      refresh_token: 'refresh_token',
      token_type: 'Bearer',
      expires_in: 3600,
    }

    act(() => {
      result.current.setUser(mockUser)
      result.current.setTokens(mockTokens)
    })

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.tokens).toEqual(mockTokens)
    expect(result.current.isAuthenticated).toBe(true)
  })

  it('handles network errors during login', async () => {
    ;(global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'))

    const { result } = renderHook(() => useAuthStore())

    await act(async () => {
      try {
        await result.current.login('test@example.com', 'password')
      } catch (error) {
        // Expected to throw
      }
    })

    expect(result.current.user).toBe(null)
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe('Login failed')
  })
})