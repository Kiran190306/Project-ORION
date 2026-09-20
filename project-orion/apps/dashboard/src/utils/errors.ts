import { ApiError } from '../api/types';

/**
 * Extracts a sanitized, human-readable error message.
 * Ensures stack traces and SQL details are never surfaced to users.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      return 'Unable to communicate with the trading engine. Please verify the backend is running.';
    }
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return 'An unexpected error occurred while processing your trading request.';
}
