import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '../src/auth/AuthContext';
import { ProtectedRoute } from '../src/auth/ProtectedRoute';
import { LoginPage } from '../src/pages/LoginPage';

describe('Authentication Flow', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders login form and prominent paper trading badge', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: /trading terminal sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getAllByText(/paper trading/i).length).toBeGreaterThan(0);
  });

  it('validates input length before submission', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    const submitBtn = screen.getByRole('button', { name: /authenticate session/i });
    await user.click(submitBtn);

    expect(await screen.findByText(/username must be at least 3 characters/i)).toBeInTheDocument();

    const usernameInput = screen.getByLabelText(/username/i);
    await user.type(usernameInput, 'trader_user');
    await user.click(submitBtn);

    expect(await screen.findByText(/password must be at least 8 characters/i)).toBeInTheDocument();
  });

  it('authenticates successfully and stores JWT token', async () => {
    const user = userEvent.setup();

    // Mock successful login response
    const mockLoginResponse = {
      access_token: 'test-jwt-token-xyz',
      token_type: 'bearer',
      user_id: 'user-uuid-1',
      username: 'trader1',
      is_superuser: false,
    };

    const mockUserResponse = {
      id: 'user-uuid-1',
      username: 'trader1',
      email: 'trader1@orion.com',
      full_name: 'Test Trader',
      is_active: true,
      is_superuser: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/login')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockLoginResponse),
        });
      }
      if (url.includes('/api/v1/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockUserResponse),
        });
      }
      return Promise.reject(new Error('Unknown URL: ' + url));
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/username/i), 'trader1');
    await user.type(screen.getByLabelText(/password/i), 'securepassword123');
    await user.click(screen.getByRole('button', { name: /authenticate session/i }));

    await waitFor(() => {
      expect(sessionStorage.getItem('orion_access_token')).toBe('test-jwt-token-xyz');
    });
  });

  it('displays user-safe error message on invalid credentials', async () => {
    const user = userEvent.setup();

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve({ detail: 'Invalid username or password' }),
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>
    );

    await user.type(screen.getByLabelText(/username/i), 'baduser');
    await user.type(screen.getByLabelText(/password/i), 'badpassword123');
    await user.click(screen.getByRole('button', { name: /authenticate session/i }));

    expect(await screen.findByText(/session expired or invalid/i)).toBeInTheDocument();
  });

  it('protects routes and redirects unauthenticated users to /login', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<div>LOGIN_PAGE_RENDERED</div>} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div>PROTECTED_CONTENT</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('LOGIN_PAGE_RENDERED')).toBeInTheDocument();
    expect(screen.queryByText('PROTECTED_CONTENT')).not.toBeInTheDocument();
  });
});
