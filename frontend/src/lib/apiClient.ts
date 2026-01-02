/**
 * JWT-enabled API Client for LLM Gateway
 *
 * Provides a centralized API client with automatic JWT token handling,
 * authentication, and error management for all backend requests.
 *
 * Features:
 * - Automatic JWT token injection from localStorage
 * - 401 handling with automatic redirect to login
 * - 403 permission denied handling
 * - Type-safe request methods
 * - Login/Logout helpers
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiClient {
  /**
   * Retrieve JWT token from localStorage
   * Returns null if running on server-side (SSR)
   */
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('jwt_token');
  }

  /**
   * Store JWT token in localStorage
   */
  private setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('jwt_token', token);
    }
  }

  /**
   * Clear JWT token from localStorage
   */
  private clearToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt_token');
    }
  }

  /**
   * Generic request method with automatic JWT injection and error handling
   *
   * @param endpoint - API endpoint (e.g., '/admin/budgets')
   * @param options - Fetch options (method, body, headers, etc.)
   * @returns Parsed JSON response
   * @throws Error on non-200 status codes
   */
  async request<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    // Add Authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized - Token expired or invalid
    if (response.status === 401) {
      this.clearToken();
      if (typeof window !== 'undefined') {
        // Redirect to login with current path for post-login redirect
        const currentPath = window.location.pathname;
        window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
      }
      throw new Error('Unauthorized - Please login again');
    }

    // Handle 403 Forbidden - Permission denied (RBAC or ownership failure)
    if (response.status === 403) {
      const error = await response.json().catch(() => ({ detail: 'Permission denied' }));
      throw new Error(error.detail || 'Permission denied');
    }

    // Handle 404 Not Found
    if (response.status === 404) {
      const error = await response.json().catch(() => ({ detail: 'Resource not found' }));
      throw new Error(error.detail || 'Resource not found');
    }

    // Handle other error status codes
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `Request failed with status ${response.status}`);
    }

    // Parse and return JSON response
    return response.json();
  }

  /**
   * GET request
   */
  async get<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * POST request
   */
  async post<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PATCH request
   */
  async patch<T = any>(endpoint: string, data: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  /**
   * DELETE request
   */
  async delete<T = any>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /**
   * Login helper - stores JWT token and user info
   *
   * @param email - User email
   * @param password - User password
   * @returns User info with token
   */
  async login(email: string, password: string): Promise<{ token: string; user: any }> {
    const response = await this.post<{ access_token: string; user: any }>('/auth/login', {
      email,
      password,
    });

    // Store token
    this.setToken(response.access_token);

    return {
      token: response.access_token,
      user: response.user,
    };
  }

  /**
   * Logout helper - clears token and redirects to login
   */
  logout(): void {
    this.clearToken();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }

  /**
   * Check if user is authenticated (has valid token)
   */
  isAuthenticated(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Get current user info from /auth/me endpoint
   */
  async getCurrentUser<T = any>(): Promise<T> {
    return this.get<T>('/auth/me');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
