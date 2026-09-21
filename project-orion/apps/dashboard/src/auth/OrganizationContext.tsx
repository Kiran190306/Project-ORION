import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { organizationApi } from '../api/endpoints';
import { getStoredOrgId, setStoredOrgId } from '../api/client';
import type { OrganizationResponse, OrganizationMemberResponse } from '../api/types';

interface OrganizationContextValue {
  organizations: OrganizationResponse[];
  currentOrg: OrganizationResponse | null;
  currentRole: string | null;
  isLoading: boolean;
  switchOrganization: (orgId: string) => Promise<void>;
  refreshOrganizations: () => Promise<void>;
}

const OrganizationContext = createContext<OrganizationContextValue | null>(null);

export const OrganizationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isAuthenticated } = useAuth();
  const [organizations, setOrganizations] = useState<OrganizationResponse[]>([]);
  const [currentOrg, setCurrentOrg] = useState<OrganizationResponse | null>(null);
  const [currentRole, setCurrentRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const resolveRole = useCallback(async (orgId: string, userId: string): Promise<string | null> => {
    try {
      const members: OrganizationMemberResponse[] = await organizationApi.listMembers(orgId);
      const userMember = members.find((m) => m.user_id === userId);
      return userMember ? userMember.role : null;
    } catch {
      return null;
    }
  }, []);

  const refreshOrganizations = useCallback(async () => {
    if (!isAuthenticated || !user) {
      setOrganizations([]);
      setCurrentOrg(null);
      setCurrentRole(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      const orgs = await organizationApi.listUserOrganizations();
      setOrganizations(orgs);

      if (orgs.length > 0) {
        const storedOrgId = getStoredOrgId();
        const matchedOrg = orgs.find((o) => o.id === storedOrgId) || orgs[0];
        setCurrentOrg(matchedOrg);
        setStoredOrgId(matchedOrg.id);

        const role = await resolveRole(matchedOrg.id, user.id);
        setCurrentRole(role || (user.is_superuser ? 'OWNER' : 'TRADER'));
      } else {
        setCurrentOrg(null);
        setCurrentRole(user.is_superuser ? 'OWNER' : 'TRADER');
        setStoredOrgId(null);
      }
    } catch {
      // Failed to list organizations
      setOrganizations([]);
      setCurrentOrg(null);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user, resolveRole]);

  useEffect(() => {
    refreshOrganizations();
  }, [refreshOrganizations]);

  const switchOrganization = async (orgId: string) => {
    const targetOrg = organizations.find((o) => o.id === orgId);
    if (!targetOrg || !user) return;

    setIsLoading(true);
    try {
      setStoredOrgId(targetOrg.id);
      setCurrentOrg(targetOrg);
      const role = await resolveRole(targetOrg.id, user.id);
      setCurrentRole(role || (user.is_superuser ? 'OWNER' : 'TRADER'));
      // Trigger a page refresh to clear stale caches and fetch with new X-Organization-ID
      window.location.reload();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <OrganizationContext.Provider
      value={{
        organizations,
        currentOrg,
        currentRole,
        isLoading,
        switchOrganization,
        refreshOrganizations,
      }}
    >
      {children}
    </OrganizationContext.Provider>
  );
};

export function useOrganization(): OrganizationContextValue {
  const context = useContext(OrganizationContext);
  if (!context) {
    throw new Error('useOrganization must be used within an OrganizationProvider');
  }
  return context;
}
