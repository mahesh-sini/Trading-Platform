/**
 * API Client Service
 * Handles all HTTP requests to the backend with authentication
 */

interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  message: string;
  error?: string;
}

interface RequestConfig {
  headers?: Record<string, string>;
  params?: Record<string, any>;
  timeout?: number;
}

export class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor() {
    this.baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: string): void {
    this.defaultHeaders['Authorization'] = `Bearer ${token}`;
  }

  /**
   * Remove authentication token
   */
  clearAuthToken(): void {
    delete this.defaultHeaders['Authorization'];
  }

  /**
   * Build URL with query parameters
   */
  private buildURL(endpoint: string, params?: Record<string, any>): string {
    const url = new URL(`${this.baseURL}/api/v1${endpoint}`);
    
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          if (Array.isArray(value)) {
            value.forEach(v => url.searchParams.append(key, v.toString()));
          } else {
            url.searchParams.append(key, value.toString());
          }
        }
      });
    }
    
    return url.toString();
  }

  /**
   * Make HTTP request
   */
  private async request<T = any>(
    method: string,
    endpoint: string,
    data?: any,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const headers = {
        ...this.defaultHeaders,
        ...config?.headers,
      };

      const url = this.buildURL(endpoint, config?.params);

      const requestConfig: RequestInit = {
        method,
        headers,
        credentials: 'include', // Include cookies for session management
      };

      if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        requestConfig.body = JSON.stringify(data);
      }

      // Add timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), config?.timeout || 30000);
      requestConfig.signal = controller.signal;

      const response = await fetch(url, requestConfig);
      clearTimeout(timeoutId);

      // Handle HTTP errors
      if (!response.ok) {
        if (response.status === 401) {
          // Handle unauthorized - redirect to login or refresh token
          this.handleUnauthorized();
        }
        
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const result = await response.json();
      return result;

    } catch (error) {
      console.error(`API request failed [${method} ${endpoint}]:`, error);
      
      // Return error response in consistent format
      return {
        success: false,
        data: null,
        message: 'Request failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Handle unauthorized responses
   */
  private handleUnauthorized(): void {
    // Clear auth token
    this.clearAuthToken();
    
    // Redirect to login page or trigger auth refresh
    if (typeof window !== 'undefined') {
      // Only redirect if we're in the browser
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/') {
        window.location.href = '/login';
      }
    }
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint, undefined, config);
  }

  /**
   * POST request
   */
  async post<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, data, config);
  }

  /**
   * PUT request
   */
  async put<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, data, config);
  }

  /**
   * PATCH request
   */
  async patch<T = any>(endpoint: string, data?: any, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('PATCH', endpoint, data, config);
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint, undefined, config);
  }

  /**
   * Upload file
   */
  async uploadFile<T = any>(
    endpoint: string,
    file: File,
    additionalData?: Record<string, any>,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    try {
      const headers = {
        ...this.defaultHeaders,
        ...config?.headers,
      };
      
      // Remove Content-Type to let browser set it with boundary
      delete headers['Content-Type'];

      const formData = new FormData();
      formData.append('file', file);

      if (additionalData) {
        Object.entries(additionalData).forEach(([key, value]) => {
          formData.append(key, value.toString());
        });
      }

      const url = this.buildURL(endpoint, config?.params);

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: formData,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      return result;

    } catch (error) {
      console.error(`File upload failed [${endpoint}]:`, error);
      return {
        success: false,
        data: null,
        message: 'File upload failed',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.get('/health');
      return response.success;
    } catch (error) {
      console.error('Health check failed:', error);
      return false;
    }
  }
}

// Create and export singleton instance
export const apiClient = new ApiClient();

// Export class for custom instances
export { ApiClient as default };