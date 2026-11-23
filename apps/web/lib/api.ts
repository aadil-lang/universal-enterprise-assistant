/**
 * Typed API Client for Acme Enterprise HR & IT Assistant API.
 * Integrates directly with FastAPI gateway:
 * - /api/v1/auth/login
 * - /api/v1/auth/me
 * - /api/v1/chat
 * - /documents/upload
 */

export interface User {
  id: string;
  email: string;
  employee_number: string;
  first_name: string;
  last_name: string;
  role: 'employee' | 'hr_admin';
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ChatCitation {
  document_title: string;
  section: string;
  page_number?: number | null;
  filename: string;
}

export interface ConfirmationPrompt {
  confirmation_token: string;
  transaction_type: string;
  summary_title: string;
  details: Record<string, any>;
  expires_at: string;
}

export interface ChatApiResponse {
  answer: string;
  category: 'policy' | 'employee' | 'hybrid' | 'out_of_scope' | 'transactional';
  citations: ChatCitation[];
  mcp_tools_used: string[];
  execution_time_ms: number;
  confirmation_required?: boolean;
  confirmation_prompt?: ConfirmationPrompt | null;
  transaction_result?: any;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 45000;

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      credentials: 'include',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errorData: any = null;
      try {
        errorData = await res.json();
      } catch {
        errorData = { detail: res.statusText || 'Unknown server error' };
      }

      const detailMsg =
        errorData?.detail && typeof errorData.detail === 'string'
          ? errorData.detail
          : errorData?.detail?.[0]?.msg || `HTTP Error ${res.status}`;

      throw new ApiError(detailMsg, res.status, errorData);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out. Please try again.', 408);
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      err?.message || 'Network error connecting to API gateway.',
      0
    );
  }
}

export const api = {
  /**
   * Authenticate user with corporate email and password.
   */
  async login(email: string, password: string): Promise<LoginResponse> {
    return request<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
    });
  },

  /**
   * Get current authenticated user profile.
   * Can use provided token or HttpOnly session cookie.
   */
  async getMe(token?: string | null): Promise<User> {
    return request<User>('/api/v1/auth/me', { method: 'GET' }, token);
  },

  /**
   * Clear authenticated session and HttpOnly cookies.
   */
  async logout(token?: string | null): Promise<void> {
    try {
      await request('/api/v1/auth/logout', { method: 'POST' }, token);
    } catch {
      // Graceful fallback if offline
    }
  },

  /**
   * Send a conversational query to the LangGraph assistant.
   */
  async sendChatMessage(
    message: string,
    token: string,
    conversationId?: string,
    confirmationAction?: 'confirm' | 'cancel',
    confirmationToken?: string
  ): Promise<ChatApiResponse> {
    return request<ChatApiResponse>(
      '/api/v1/chat',
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message.trim(),
          ...(conversationId ? { conversation_id: conversationId } : {}),
          ...(confirmationAction ? { confirmation_action: confirmationAction } : {}),
          ...(confirmationToken ? { confirmation_token: confirmationToken } : {}),
        }),
      },
      token
    );
  },

  /**
   * Upload an enterprise policy document (HR Admin only).
   */
  async uploadDocument(
    file: File,
    title: string,
    category: 'HR' | 'IT',
    token: string
  ): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (title.trim()) {
      formData.append('title', title.trim());
    }
    formData.append('category', category);

    return request<any>(
      '/documents/upload',
      {
        method: 'POST',
        body: formData,
      },
      token
    );
  },
};
