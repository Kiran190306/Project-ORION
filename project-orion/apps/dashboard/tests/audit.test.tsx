import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { AuditPage } from '../src/pages/AuditPage';
import { ToastProvider } from '../src/components/common/Toast';
import { AuthProvider } from '../src/auth/AuthContext';
import { OrganizationProvider } from '../src/auth/OrganizationContext';
import type {
  OrganizationResponse,
  OrganizationMemberResponse,
  AuditLogResponse,
} from '../src/api/types';

const mockOrg: OrganizationResponse = {
  id: 'org-test-1234',
  name: 'Acme Capital Management',
  slug: 'acme-capital',
  status: 'ACTIVE',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const mockMembers: OrganizationMemberResponse[] = [
  {
    id: 'mem-1',
    organization_id: 'org-test-1234',
    user_id: 'usr-auditor-1',
    role: 'AUDITOR',
    status: 'ACTIVE',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockAuditLogs: AuditLogResponse[] = [
  {
    id: 'audit-1',
    organization_id: 'org-test-1234',
    event_type: 'ORDER_PLACED',
    component: 'ORDER_ENGINE',
    actor: 'usr-trader-2',
    details: {
      symbol: 'EUR/USD',
      side: 'BUY',
      quantity: 10000,
      client_token: '[REDACTED]',
    },
    timestamp: new Date().toISOString(),
  },
  {
    id: 'audit-2',
    organization_id: 'org-test-1234',
    event_type: 'MEMBER_INVITED',
    component: 'AUTH_ENGINE',
    actor: 'usr-owner-1',
    details: {
      email: 'analyst@acme.com',
      role: 'TRADER',
    },
    timestamp: new Date().toISOString(),
  },
];

describe('AuditPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.setItem('orion_access_token', 'mock-jwt-token');
    sessionStorage.setItem('orion_active_org_id', 'org-test-1234');
  });

  it('renders compliance audit logs with event type, actor, and component', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () =>
            Promise.resolve({
              id: 'usr-auditor-1',
              username: 'auditor_user',
              email: 'auditor@acme.com',
              is_active: true,
              is_superuser: false,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }),
        });
      }
      if (url.includes('/api/v1/organizations/org-test-1234/audit-logs')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockAuditLogs),
        });
      }
      if (url.includes('/api/v1/organizations/org-test-1234/members')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockMembers),
        });
      }
      if (url.includes('/api/v1/organizations')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve([mockOrg]),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({}),
      });
    });

    render(
      <MemoryRouter>
        <ToastProvider>
          <AuthProvider>
            <OrganizationProvider>
              <AuditPage />
            </OrganizationProvider>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Compliance Audit Trail')).toBeInTheDocument();
    expect(await screen.findByText('ORDER_PLACED')).toBeInTheDocument();
    expect(await screen.findByText('MEMBER_INVITED')).toBeInTheDocument();
    expect(screen.getByText('usr-trader-2')).toBeInTheDocument();
    expect(screen.getByText('ORDER_ENGINE')).toBeInTheDocument();
  });

  it('opens payload modal and shows redacted details', async () => {
    const user = userEvent.setup();

    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () =>
            Promise.resolve({
              id: 'usr-auditor-1',
              username: 'auditor_user',
              email: 'auditor@acme.com',
              is_active: true,
              is_superuser: false,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }),
        });
      }
      if (url.includes('/api/v1/organizations/org-test-1234/audit-logs')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockAuditLogs),
        });
      }
      if (url.includes('/api/v1/organizations/org-test-1234/members')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockMembers),
        });
      }
      if (url.includes('/api/v1/organizations')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve([mockOrg]),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({}),
      });
    });

    render(
      <MemoryRouter>
        <ToastProvider>
          <AuthProvider>
            <OrganizationProvider>
              <AuditPage />
            </OrganizationProvider>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    );

    const viewBtns = await screen.findAllByRole('button', { name: /view payload/i });
    await user.click(viewBtns[0]);

    expect(await screen.findByText('Audit Payload Details')).toBeInTheDocument();
    expect(screen.getByText(/\[REDACTED\]/)).toBeInTheDocument();
  });
});
