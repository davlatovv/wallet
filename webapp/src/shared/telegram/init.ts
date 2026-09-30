import {
  backButton,
  bindMiniAppCssVars,
  bindThemeParamsCssVars,
  isTMA,
  miniAppReady,
  mockTelegramEnv,
  mountBackButton,
  // The plain `mount*` functions are deprecated and asynchronous (they
  // return a promise); calling bindCssVars() right after them raced ahead
  // of mounting and threw FunctionNotAvailableError. The Sync variants
  // mount synchronously, which is what a fire-and-forget boot needs here.
  mountMiniAppSync,
  mountThemeParamsSync,
} from '@telegram-apps/sdk-react';
import { init } from '@telegram-apps/sdk-react';

declare global {
  interface Window {
    TelegramWebviewProxy?: { postEvent: (event: string, data?: string) => void };
  }
}

/**
 * A plausible, UNSIGNED set of launch params used only to render the app
 * with real-looking data when opened as a plain web page (not inside
 * Telegram). Its `hash` will not pass server-side validation — that is
 * intentional: `POST /auth/telegram` (see app/presentation/api/auth) must
 * reject anything not actually signed by the bot token, so login in this
 * mode fails visibly (see src/shared/api/auth.ts) rather than pretending to
 * work. Real end-to-end testing needs the real Telegram client (open the
 * dev tunnel URL from a chat — see docs/MINIAPP_PLAN.md task 0.4).
 */
function devMockLaunchParams(): void {
  const now = Math.floor(Date.now() / 1000);
  // A URLSearchParams instance (not a manually-joined string): the outer
  // launch-params serializer percent-encodes this value exactly once when
  // building the full query string; pre-encoding it ourselves would double
  // it. `signature` is required by the current InitData schema (its
  // absence throws InvalidLaunchParamsError — "Expected signature but
  // received undefined" — found by testing parseLaunchParamsQuery directly
  // in the browser console).
  const initData = new URLSearchParams({
    user: JSON.stringify({ id: 1, first_name: 'Dev', username: 'dev_user', language_code: 'ru' }),
    auth_date: String(now),
    // Deliberately unsigned/unverifiable — see the doc comment above.
    signature: 'dev',
    hash: '0000000000000000000000000000000000000000000000000000000000000000',
  });

  mockTelegramEnv({
    launchParams: {
      tgWebAppPlatform: 'tdesktop',
      tgWebAppVersion: '8.0',
      tgWebAppThemeParams: {
        bg_color: '#ffffff',
        secondary_bg_color: '#f0f0f1',
        text_color: '#000000',
        hint_color: '#8e8e93',
        link_color: '#2aabee',
        button_color: '#2aabee',
        button_text_color: '#ffffff',
        destructive_text_color: '#ff3b30',
      },
        tgWebAppData: initData,
    },
  });
}

let initialized = false;

/**
 * True once initTelegram() has installed the no-op transport shim below —
 * i.e. there is no real Telegram client on the other end of any postEvent
 * call. Exported so callers that need an actual response (e.g. a popup)
 * can tell a genuinely-unsupported feature apart from one that would hang
 * forever waiting on a reply nothing will ever send — see
 * shared/telegram/confirmDialog.ts, which hit exactly that hang testing
 * the native popup here.
 */
export let usingMockTransport = false;

/**
 * Boots the Telegram SDK once per app lifetime: mocks the environment when
 * running outside Telegram (local dev in a plain browser), then mounts the
 * mini-app, theme and back-button scopes and binds their state to CSS
 * variables consumed by shared/theme/tokens.css.
 */
export function initTelegram(): void {
  if (initialized) return;
  initialized = true;

  if (!isTMA()) {
    devMockLaunchParams();
  }

  // A real Telegram client always provides one of: window.TelegramWebviewProxy
  // (native apps), being loaded inside an iframe (Telegram Web, which talks
  // to window.parent via postMessage), or window.external.notify (old
  // Windows Phone clients). None of those exist in a plain top-level
  // browser tab, so init() falls through every transport postEvent knows
  // and throws UnknownEnvError — found by calling it directly in the
  // browser console and checking window.TelegramWebviewProxy afterwards.
  // A no-op shim is enough: nothing this app calls needs a real response
  // back from a native client during local dev.
  //
  // This has to be its own check, independent of isTMA() above: isTMA()
  // reads sessionStorage, which survives a plain reload even though
  // window.TelegramWebviewProxy (never persisted) does not — a reload that
  // reused stored mock launch params skipped this shim entirely and threw
  // exactly the error above (a real bug hit and fixed while testing this
  // in the browser). Gating on "no real transport exists" instead of
  // isTMA() keeps this safe to run unconditionally: a genuine Telegram Web
  // (iframe) session always has window.parent !== window, so it never
  // takes this branch and always gets the real postMessage path.
  const hasRealTransport =
    window.parent !== window ||
    !!window.TelegramWebviewProxy ||
    !!(window.external as { notify?: unknown } | null)?.notify;
  if (!hasRealTransport) {
    window.TelegramWebviewProxy = { postEvent: () => {} };
    usingMockTransport = true;
  }

  init();

  mountMiniAppSync();
  bindMiniAppCssVars();

  mountThemeParamsSync();
  bindThemeParamsCssVars();

  if (backButton.isSupported()) {
    mountBackButton();
  }

  miniAppReady();
}
