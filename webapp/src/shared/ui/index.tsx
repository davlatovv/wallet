import type { CSSProperties, ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { t } from '../i18n';
import { useTelegramBackButton } from '../telegram/useBackButton';

export function Screen({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        minHeight: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--color-bg-secondary)',
      }}
    >
      {children}
    </div>
  );
}

export function ScreenBody({
  children,
  withTabBar = true,
}: {
  children: ReactNode;
  withTabBar?: boolean;
}) {
  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: `12px var(--space-screen-x) ${withTabBar ? 96 : 24}px`,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      {children}
    </div>
  );
}

export function Header({ title, right }: { title: string; right?: ReactNode }) {
  return (
    <div
      style={{
        height: 56,
        minHeight: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        background: 'var(--color-bg)',
        borderBottom: '1px solid var(--color-separator)',
        position: 'sticky',
        top: 0,
        zIndex: 1,
      }}
    >
      <div style={{ fontSize: 17, fontWeight: 600 }}>{title}</div>
      {right ?? <div style={{ width: 1 }} />}
    </div>
  );
}

export function Card({ children, padding = '16px' }: { children: ReactNode; padding?: string }) {
  return (
    <div
      style={{
        background: 'var(--color-bg)',
        borderRadius: 'var(--radius-card)',
        padding,
      }}
    >
      {children}
    </div>
  );
}

export function SectionHeader({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: 13,
        fontWeight: 600,
        color: 'var(--color-hint)',
        textTransform: 'uppercase',
        letterSpacing: 0.3,
        padding: '4px 4px 0',
      }}
    >
      {children}
    </div>
  );
}

export function ListItem({
  left,
  right,
  onClick,
  href,
  border = true,
}: {
  left: ReactNode;
  right?: ReactNode;
  onClick?: () => void;
  href?: string;
  border?: boolean;
}) {
  const style: CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    minHeight: 56,
    padding: '8px 4px',
    border: 'none',
    borderBottom: border ? '1px solid var(--color-separator)' : 'none',
    color: 'var(--color-text)',
    textDecoration: 'none',
    background: 'none',
    width: '100%',
    textAlign: 'left',
    cursor: onClick || href ? 'pointer' : 'default',
  };
  const content = (
    <>
      {left}
      {right}
    </>
  );
  if (href) {
    return (
      <NavLink to={href} style={style}>
        {content}
      </NavLink>
    );
  }
  return (
    <button type="button" onClick={onClick} style={style} disabled={!onClick}>
      {content}
    </button>
  );
}

export function IconAvatar({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'accent' }) {
  return (
    <div
      style={{
        width: 40,
        height: 40,
        borderRadius: 12,
        background: tone === 'accent' ? 'var(--color-link)' : 'var(--color-bg-secondary)',
        color: tone === 'accent' ? 'var(--color-button-text)' : 'inherit',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 18,
        flexShrink: 0,
      }}
    >
      {children}
    </div>
  );
}

export function ProgressBar({ percent, color }: { percent: number; color?: string }) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div
      style={{
        height: 8,
        borderRadius: 4,
        background: 'var(--color-separator)',
        width: '100%',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: 8,
          borderRadius: 4,
          width: `${clamped}%`,
          background: color ?? 'var(--color-link)',
          transition: 'width 0.2s ease',
        }}
      />
    </div>
  );
}

export function StatTile({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
      <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>{label}</div>
      <div
        style={{
          fontSize: 16,
          fontWeight: 700,
          color: color ?? 'var(--color-text)',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {value}
      </div>
    </div>
  );
}

export function PrimaryButton({
  children,
  onClick,
  href,
  variant = 'filled',
}: {
  children: ReactNode;
  onClick?: () => void;
  href?: string;
  variant?: 'filled' | 'outline';
}) {
  const style: CSSProperties = {
    display: 'block',
    textAlign: 'center',
    padding: '14px 0',
    borderRadius: 'var(--radius-control)',
    fontSize: 15,
    fontWeight: 600,
    textDecoration: 'none',
    cursor: 'pointer',
    border: variant === 'outline' ? '1px dashed var(--color-link)' : 'none',
    background: variant === 'filled' ? 'var(--color-button)' : 'transparent',
    color: variant === 'filled' ? 'var(--color-button-text)' : 'var(--color-link)',
    width: '100%',
  };
  if (href) {
    return (
      <NavLink to={href} style={style}>
        {children}
      </NavLink>
    );
  }
  return (
    <button type="button" onClick={onClick} style={style}>
      {children}
    </button>
  );
}

export function EmptyState({ title, note }: { title: string; note?: string }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        padding: '48px 24px',
        color: 'var(--color-hint)',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text)' }}>{title}</div>
      {note && <div style={{ fontSize: 13 }}>{note}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 12,
        padding: '48px 24px',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 15, color: 'var(--color-destructive)' }}>{message}</div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            border: 'none',
            background: 'none',
            color: 'var(--color-link)',
            fontSize: 15,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {t.common.retry}
        </button>
      )}
    </div>
  );
}

const TABS = [
  { key: 'home', to: '/', label: t.tabs.home, glyph: '⌂' },
  { key: 'transactions', to: '/transactions', label: t.tabs.transactions, glyph: '≡' },
  { key: 'analytics', to: '/analytics', label: t.tabs.analytics, glyph: '◔' },
  { key: 'more', to: '/more', label: t.tabs.more, glyph: '•••' },
] as const;

export function TabBar() {
  return (
    <nav
      style={{
        position: 'fixed',
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        background: 'var(--color-bg)',
        borderTop: '1px solid var(--color-separator)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.key}
          to={tab.to}
          end={tab.to === '/'}
          style={({ isActive }) => ({
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 2,
            padding: '8px 0',
            textDecoration: 'none',
            color: isActive ? 'var(--color-link)' : 'var(--color-hint)',
          })}
        >
          <div style={{ fontSize: 20, lineHeight: 1 }}>{tab.glyph}</div>
          <div style={{ fontSize: 11, fontWeight: 600 }}>{tab.label}</div>
        </NavLink>
      ))}
    </nav>
  );
}

/**
 * A screen reached from a tab (never a tab itself): shows Telegram's
 * hardware back button instead of the TabBar, per the nav map.
 */
export function SubScreen({ title, children }: { title: string; children: ReactNode }) {
  useTelegramBackButton();
  return (
    <Screen>
      <Header title={title} />
      <ScreenBody withTabBar={false}>{children}</ScreenBody>
    </Screen>
  );
}

const fieldInputStyle: CSSProperties = {
  background: 'var(--color-bg)',
  border: 'none',
  borderRadius: 'var(--radius-control)',
  padding: '12px 14px',
  fontSize: 15,
  color: 'var(--color-text)',
  outline: 'none',
  width: '100%',
};

/** Label + input, consistent across the reminder-creation forms. */
export function FormField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontSize: 13, color: 'var(--color-hint)', fontWeight: 600 }}>{label}</div>
      {children}
    </div>
  );
}

export function TextField({
  value,
  onChange,
  placeholder,
  type = 'text',
  inputMode,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  inputMode?: 'text' | 'decimal' | 'numeric';
}) {
  return (
    <input
      type={type}
      inputMode={inputMode}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      style={fieldInputStyle}
    />
  );
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div style={{ display: 'flex', background: 'var(--color-bg-secondary)', borderRadius: 12, padding: 3, gap: 3 }}>
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          style={{
            flex: 1,
            textAlign: 'center',
            padding: '9px 0',
            borderRadius: 9,
            fontSize: 13,
            fontWeight: value === opt.value ? 600 : 400,
            border: 'none',
            cursor: 'pointer',
            background: value === opt.value ? 'var(--color-link)' : 'transparent',
            color: value === opt.value ? 'var(--color-button-text)' : 'var(--color-text)',
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
