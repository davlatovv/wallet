import { backButton } from '@telegram-apps/sdk-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Shows Telegram's hardware back button while the calling screen is mounted
 * and wires it to router history. The four tab-bar screens (Home,
 * Transactions, Analytics, More) never call this — Telegram's own chrome
 * has no back button there, matching the nav map in docs/MINIAPP_PLAN.md.
 */
export function useTelegramBackButton(): void {
  const navigate = useNavigate();

  useEffect(() => {
    if (!backButton.isSupported() || !backButton.isMounted()) return;

    backButton.show();
    const off = backButton.onClick(() => navigate(-1));

    return () => {
      off();
      backButton.hide();
    };
  }, [navigate]);
}
