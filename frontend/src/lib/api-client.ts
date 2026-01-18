/**
 * API Client for backend communication with JWT authentication
 */

const API_BASE_URL = '/api';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

interface RequestOptions extends Omit<RequestInit, 'method' | 'headers' | 'body'> {
  token?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private getToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  private buildHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    const authToken = token || this.getToken();
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || `HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  }

  private async request<T>(
    method: HttpMethod,
    endpoint: string,
    data?: unknown,
    options: RequestOptions = {}
  ): Promise<T> {
    const { token, ...fetchOptions } = options;
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method,
      headers: this.buildHeaders(token),
      body: data ? JSON.stringify(data) : undefined,
      ...fetchOptions,
    });
    return this.handleResponse<T>(response);
  }

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', endpoint, undefined, options);
  }

  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', endpoint, data, options);
  }

  async put<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', endpoint, data, options);
  }

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', endpoint, undefined, options);
  }

  async patch<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T> {
    return this.request<T>('PATCH', endpoint, data, options);
  }
}

export const apiClient = new ApiClient();
export default ApiClient;
