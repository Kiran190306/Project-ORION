/**
 * Institutional HTTP client for Project ORION.
 *
 * Handles:
 * - JWT Authorization header injection
 * - Correlation ID propagation (X-Correlation-ID)
 * - Centralized response parsing and HTTP error normalization
 * - Safe error translation without leaked stack traces or sensitive internals
 */

import { ApiError, ApiErrorResponse } from './types';

// Configuration: uses VITE_API_URL or defaults to empty string for reverse proxy
const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

export function getStoredToken(): string | null {
  try {
    return sessionStorage.getItem('orion_access_token');
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      sessionStorage.setItem('orion_access_token', token);
    } else {
      sessionStorage.removeItem('orion_access_token');
    }
  } catch {
    // Ignore storage quota or access errors
  }
}

export function getStoredOrgId(): string | null {
  try {
    return sessionStorage.getItem('orion_active_org_id');
  } catch {
    return null;
  }
}

export function setStoredOrgId(orgId: string | null): void {
  try {
    if (orgId) {
      sessionStorage.setItem('orion_active_org_id', orgId);
    } else {
      sessionStorage.removeItem('orion_active_org_id');
    }
  } catch {
    // Ignore storage quota or access errors
  }
}


function generateCorrelationId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'cid-' + Math.random().toString(36).substring(2, 15);
}

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers: customHeaders, ...fetchOptions } = options;

  let url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += (url.includes('?') ? '&' : '?') + queryString;
    }
  }

  const token = getStoredToken();
  const orgId = getStoredOrgId();
  const correlationId = generateCorrelationId();

  const headers = new Headers(customHeaders);
  headers.set('Accept', 'application/json');
  if (fetchOptions.body && !(fetchOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (orgId && !headers.has('X-Organization-ID')) {
    headers.set('X-Organization-ID', orgId);
  }
  if (!headers.has('X-Correlation-ID')) {
    headers.set('X-Correlation-ID', correlationId);
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchOptions,
      headers,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network error';
    throw new ApiError(0, `Unable to connect to trading engine: ${message}`, correlationId);
  }

  const resCorrelationId = response.headers.get('x-correlation-id') || correlationId;

  if (!response.ok) {
    let errorDetail: unknown = null;
    let errorMessage = `Request failed with status ${response.status}`;

    try {
      const errorJson: ApiErrorResponse = await response.json();
      errorDetail = errorJson;

      if (typeof errorJson.detail === 'string') {
        errorMessage = errorJson.detail;
      } else if (Array.isArray(errorJson.detail)) {
        // Pydantic validation error array
        errorMessage = errorJson.detail.map((d) => d.msg || 'Invalid field').join(', ');
      } else if (errorJson.message) {
        errorMessage = errorJson.message;
      } else if (errorJson.error) {
        errorMessage = errorJson.error;
      }
    } catch {
      // Body not JSON
    }

    // Standard institutional user-facing error message mapping
    let sanitizedMessage = errorMessage;
    switch (response.status) {
      case 400:
        sanitizedMessage = errorMessage || 'Invalid trading request.';
        break;
      case 401:
        sanitizedMessage = 'Session expired or invalid. Please sign in again.';
        setStoredToken(null);
        setStoredOrgId(null);
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('orion:unauthorized'));
        }
        break;
      case 403:
        sanitizedMessage = errorMessage || 'You are not authorized to perform this action.';
        break;
      case 404:
        sanitizedMessage = errorMessage || 'The requested resource was not found.';
        break;
      case 409:
        sanitizedMessage = errorMessage || 'The operation conflicts with the current state.';
        break;
      case 422:
        sanitizedMessage = `Validation error: ${errorMessage}`;
        break;
      case 429: {
        const retryAfterHeader = response.headers.get('retry-after');
        const retryAfterNum = retryAfterHeader ? parseInt(retryAfterHeader, 10) : NaN;
        if (!isNaN(retryAfterNum) && retryAfterNum > 0) {
          sanitizedMessage = `Rate limit exceeded. Please retry after ${retryAfterNum} seconds.`;
        } else {
          sanitizedMessage = errorMessage || 'Rate limit exceeded. Please try again shortly.';
        }
        break;
      }
      case 500:
      case 502:
      case 503:
      case 504:
        sanitizedMessage = 'Trading service is temporarily unavailable.';
        break;
    }

    const retryAfterHeader = response.headers.get('retry-after');
    const retryAfterSeconds = retryAfterHeader && !isNaN(parseInt(retryAfterHeader, 10))
      ? parseInt(retryAfterHeader, 10)
      : undefined;

    throw new ApiError(response.status, sanitizedMessage, resCorrelationId, errorDetail, retryAfterSeconds);
  }

  // HTTP 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    return {} as T;
  }
}
