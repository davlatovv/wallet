import { ru } from './messages/ru';

/** v1 ships Russian only; the type keeps every consumer ready for more. */
export type Locale = 'ru';

export const locale: Locale = 'ru';

/** `t.home.totalBalance`, etc. — swap for a real lookup once a second
 * locale exists (Phase 6 backlog); call sites don't change either way. */
export const t = ru;
