import createClient from 'openapi-fetch';
import type { paths } from './schema';
import { clearAccessToken, getAccessToken } from './auth';

export const apiClient = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
});

apiClient.use({
  async onRequest({ request }) {
    // /auth/telegram itself needs no token — it's how one is obtained.
    if (request.url.endsWith('/api/v1/auth/telegram')) return request;
    const token = await getAccessToken();
    request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  },
  async onResponse({ response }) {
    if (response.status === 401) {
      // The cached token is gone or expired; the next request (a query
      // retry, or the user's next action) re-authenticates from scratch.
      clearAccessToken();
    }
    return response;
  },
});

/** True for the 401 shape RETRY_ON_AUTH below matches on. */
export function isAuthError(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    (error as { code: unknown }).code === 'unauthorized'
  );
}

/** Pass as a query's `retry` option: one extra attempt after a 401 (which by
 * then has a freshly re-authenticated token), otherwise no retries — this
 * app calls its own backend, so a failure is rarely transient. */
export function retryOnceOnAuthError(failureCount: number, error: unknown): boolean {
  return failureCount < 1 && isAuthError(error);
}
