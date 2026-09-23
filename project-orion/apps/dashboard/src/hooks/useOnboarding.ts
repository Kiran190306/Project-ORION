import { useState, useEffect, useCallback } from 'react';
import { onboardingApi } from '../api/endpoints';
import type { OnboardingStatusResponse, OnboardingStep } from '../api/types';
import { useAuth } from '../auth/AuthContext';
import { useOrganization } from '../auth/OrganizationContext';
import { getErrorMessage } from '../utils/errors';

export interface UseOnboardingReturn {
  status: OnboardingStatusResponse | null;
  isLoading: boolean;
  error: string | null;
  isSubmitting: boolean;
  isOnboardingActive: boolean;
  refreshStatus: () => Promise<OnboardingStatusResponse | null>;
  completeStep: (
    step: OnboardingStep,
    metadata?: Record<string, any>
  ) => Promise<OnboardingStatusResponse>;
}

export function useOnboarding(): UseOnboardingReturn {
  const { isAuthenticated, user } = useAuth();
  const { currentOrg, isLoading: isOrgLoading } = useOrganization();

  const [status, setStatus] = useState<OnboardingStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const refreshStatus = useCallback(async (): Promise<OnboardingStatusResponse | null> => {
    if (!isAuthenticated || !user || !currentOrg) {
      setStatus(null);
      setIsLoading(false);
      return null;
    }

    try {
      setIsLoading(true);
      setError(null);
      const res = await onboardingApi.getStatus();
      setStatus(res);
      return res;
    } catch (err) {
      const msg = getErrorMessage(err);
      setError(msg);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, user, currentOrg]);

  useEffect(() => {
    // Only query onboarding status when org resolution is done
    if (!isOrgLoading && isAuthenticated && currentOrg) {
      refreshStatus();
    } else if (!isAuthenticated || (!isOrgLoading && !currentOrg)) {
      setIsLoading(false);
      setStatus(null);
    }
  }, [isOrgLoading, isAuthenticated, currentOrg, refreshStatus]);

  const completeStep = useCallback(
    async (
      step: OnboardingStep,
      metadata?: Record<string, any>
    ): Promise<OnboardingStatusResponse> => {
      setIsSubmitting(true);
      setError(null);
      try {
        const payload = metadata ? { metadata } : undefined;
        const res = await onboardingApi.completeStep(step, payload);
        setStatus(res);
        return res;
      } catch (err) {
        const msg = getErrorMessage(err);
        setError(msg);
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  const isOnboardingActive = Boolean(status && status.status !== 'COMPLETED');

  return {
    status,
    isLoading: isLoading || isOrgLoading,
    error,
    isSubmitting,
    isOnboardingActive,
    refreshStatus,
    completeStep,
  };
}
