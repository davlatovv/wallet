import { isPopupSupported, showPopup } from '@telegram-apps/sdk-react';
import { usingMockTransport } from './init';

/**
 * Destructive-action confirmation. Prefers Telegram's native popup
 * (consistent look, and the only thing guaranteed to work across every
 * Telegram client); falls back to `window.confirm` outside Telegram (local
 * dev — see shared/telegram/init.ts) or on clients too old to support it.
 *
 * `usingMockTransport` matters here specifically: `isPopupSupported()` is a
 * version check, so it can read true in the local-dev mock even though
 * nothing is on the other end to answer — `showPopup()` then hangs forever
 * waiting for a reply, and every later call fails with "A popup is already
 * opened" once one is stuck like that. Found exactly this way testing the
 * transaction delete flow in this browser: the popup never resolved, and
 * it locked out every subsequent confirm for the rest of the session.
 */
export async function confirmDialog(message: string): Promise<boolean> {
  if (isPopupSupported() && !usingMockTransport) {
    const buttonId = await showPopup({
      message,
      buttons: [
        { id: 'confirm', type: 'destructive', text: 'Удалить' },
        { id: 'cancel', type: 'cancel' },
      ],
    });
    return buttonId === 'confirm';
  }
  return window.confirm(message);
}
