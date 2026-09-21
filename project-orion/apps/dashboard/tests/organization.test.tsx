import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { OrganizationPage } from '../src/pages/OrganizationPage';
import { ToastProvider } from '../src/components/common/Toast';
import { AuthProvider } from '../src/auth/AuthContext';
import { OrganizationProvider } from '../src/auth/OrganizationContext';
import type {
  OrganizationResponse,
  OrganizationMemberResponse,
  InvitationResponse,
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
    user_id: 'usr-owner-1',
    role: 'OWNER',
    status: 'ACTIVE',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'mem-2',
    organization_id: 'org-test-1234',
    user_id: 'usr-trader-2',
    role: 'TRADER',
    status: 'ACTIVE',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockInvite: InvitationResponse = {
  id: 'inv-1',
  organization_id: 'org-test-1234',
  email: 'analyst@acme.com',
  role: 'PORTFOLIO_MANAGER',
  status: 'PENDING',
  invited_by_user_id: 'usr-owner-1',
  expires_at: new Date(Date.now() + 86400000).toISOString(),
  created_at: new Date().toISOString(),
  invitation_token: 'secret-token-xyz-123',
  invitation_url: '/api/v1/invitations/secret-token-xyz-123/accept',
};

describe('OrganizationPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.setItem('orion_access_token', 'mock-jwt-token');
    sessionStorage.setItem('orion_active_org_id', 'org-test-1234');
  });

  it('renders organization details, active role, and members table', async () => {
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/v1/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () =>
            Promise.resolve({
              id: 'usr-owner-1',
              username: 'owner_user',
              email: 'owner@acme.com',
              is_active: true,
              is_superuser: true,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }),
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
              <OrganizationPage />
            </OrganizationProvider>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText('Organization Governance')).toBeInTheDocument();
    expect(await screen.findByText('Acme Capital Management')).toBeInTheDocument();
    expect(await screen.findByText('acme-capital')).toBeInTheDocument();
    expect(await screen.findByText('usr-trader-2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /invite member/i })).toBeInTheDocument();
  });

  it('allows opening invite modal and generating an invitation', async () => {
    const user = userEvent.setup();

    global.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes('/api/v1/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () =>
            Promise.resolve({
              id: 'usr-owner-1',
              username: 'owner_user',
              email: 'owner@acme.com',
              is_active: true,
              is_superuser: true,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }),
        });
      }
      if (url.includes('/members/invite') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          status: 201,
          headers: new Headers({ 'content-type': 'application/json' }),
          json: () => Promise.resolve(mockInvite),
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
              <OrganizationPage />
            </OrganizationProvider>
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    );

    const inviteBtn = await screen.findByRole('button', { name: /invite member/i });
    await user.click(inviteBtn);

    expect(screen.getByText('Invite New Organization Member')).toBeInTheDocument();
    const emailInput = screen.getByPlaceholderText('colleague@institution.com');
    await user.type(emailInput, 'analyst@acme.com');

    const submitBtn = screen.getByRole('button', { name: /generate cryptographic invitation/i });
    await user.click(submitBtn);

    expect(await screen.findByText('Invitation Successfully Created')).toBeInTheDocument();
    expect(screen.getByDisplayValue('secret-token-xyz-123')).toBeInTheDocument();
  });
});
