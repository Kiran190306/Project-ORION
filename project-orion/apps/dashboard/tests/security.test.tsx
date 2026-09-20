import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient, setStoredToken, getStoredToken } from '../src/api/client';
import { ApiError } from '../src/api/types';

describe('Security & Authorization Tests', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('clears session and dispatches unauthorized event on HTTP 401', async () => {
    setStoredToken('expired-or-invalid-token');
    expect(getStoredToken()).toBe('expired-or-invalid-token');

    const unauthorizedListener = vi.fn();
    window.addEventListener('orion:unauthorized', unauthorizedListener);

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ detail: 'Token has expired' }),
    });

    await expect(apiClient('/api/v1/orders/')).rejects.toThrow(
      'Session expired or invalid. Please sign in again.'
    );

    expect(getStoredToken()).toBeNull();
    expect(unauthorizedListener).toHaveBeenCalledTimes(1);

    window.removeEventListener('orion:unauthorized', unauthorizedListener);
  });

  it('sanitizes HTTP 403 Forbidden errors without leaking sensitive backend details', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ detail: 'Access forbidden: cross-account IDOR violation' }),
    });

    try {
      await apiClient('/api/v1/orders/forbidden-id');
      expect.unreachable('Should have thrown 403');
    } catch (err: unknown) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.statusCode).toBe(403);
      expect(apiErr.message).toContain('Access forbidden');
    }
  });

  it('injects X-Correlation-ID and Authorization headers on all requests', async () => {
    setStoredToken('sample-valid-token');

    let capturedHeaders: Headers | null = null;
    global.fetch = vi.fn().mockImplementation((_url: string, opts: RequestInit) => {
      capturedHeaders = opts.headers as Headers;
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({ ok: true }),
      });
    });

    await apiClient('/api/v1/dashboard/');

    expect(capturedHeaders).not.toBeNull();
    expect((capturedHeaders as unknown as Headers).get('Authorization')).toBe('Bearer sample-valid-token');
    expect((capturedHeaders as unknown as Headers).get('X-Correlation-ID')).toBeTruthy();
  });
});
