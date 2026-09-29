import { retrieveRawInitData } from '@telegram-apps/sdk-react';

/**
 * The access token lives in memory only, not localStorage/sessionStorage:
 * it's short-lived (see JWT_TTL_MINUTES on the backend) and re-derived from
 * Telegram's own initData on every fresh page load, so persisting it buys
 * nothing and just widens the window for XSS token theft.
 */
let accessToken: string | null = null;
let loginPromise: Promise<string> | null = null;

export class AuthError extends Error {}

async function loginWithTelegram(): Promise<string> {
  const initData = retrieveRawInitData();
  if (!initData) {
    throw new AuthError('No Telegram initData available — open this app from Telegram.');
  }

  const base = import.meta.env.VITE_API_BASE_URL ?? '';
  const res = await fetch(`${base}/api/v1/auth/telegram`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initData }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new AuthError(body?.message ?? `Login failed (${res.status})`);
  }

  const data: { access_token: string } = await res.json();
  return data.access_token;
}

/** Returns a cached token, or logs in once (concurrent callers share the one request). */
export async function getAccessToken(): Promise<string> {
  if (accessToken) return accessToken;
  if (!loginPromise) {
    loginPromise = loginWithTelegram()
      .then((token) => {
        accessToken = token;
        return token;
      })
      .finally(() => {
        loginPromise = null;
      });
  }
  return loginPromise;
}

/** Drops the cached token so the next request re-authenticates (e.g. after a 401). */
export function clearAccessToken(): void {
  accessToken = null;
}

/** Forces a fresh login, bypassing any cached token. */
export async function reauthenticate(): Promise<string> {
  clearAccessToken();
  return getAccessToken();
}
