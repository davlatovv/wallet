import { t } from '../../shared/i18n';
import { Card, Header, IconAvatar, ListItem, Screen, ScreenBody, SectionHeader, TabBar } from '../../shared/ui';

const FINANCE_ITEMS = [
  { icon: '📂', label: t.more.categories, to: '/categories' },
  { icon: '🎯', label: t.more.budgets, to: '/budgets' },
  { icon: '💳', label: t.more.debts, to: '/debts' },
  { icon: '🏦', label: t.more.savings, to: '/savings' },
  { icon: '🔔', label: t.more.reminders, to: '/reminders' },
];

export function MorePage() {
  return (
    <Screen>
      <Header title={t.more.title} />
      <ScreenBody>
        <SectionHeader>{t.more.finance}</SectionHeader>
        <Card padding="4px 12px">
          {FINANCE_ITEMS.map((item, i) => (
            <ListItem
              key={item.to}
              href={item.to}
              border={i < FINANCE_ITEMS.length - 1}
              left={
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <IconAvatar>{item.icon}</IconAvatar>
                  <div style={{ fontSize: 15 }}>{item.label}</div>
                </div>
              }
              right={<span style={{ color: 'var(--color-hint)', fontSize: 17 }}>›</span>}
            />
          ))}
        </Card>

        <SectionHeader>{t.more.data}</SectionHeader>
        <Card padding="4px 12px">
          <ListItem
            href="/export"
            border={false}
            left={
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <IconAvatar>📤</IconAvatar>
                <div style={{ fontSize: 15 }}>{t.more.export}</div>
              </div>
            }
            right={<span style={{ color: 'var(--color-hint)', fontSize: 17 }}>›</span>}
          />
        </Card>

        <div style={{ textAlign: 'center', color: 'var(--color-hint)', fontSize: 12, marginTop: 'auto' }}>
          Wallet Bot · Mini App v1
        </div>
      </ScreenBody>
      <TabBar />
    </Screen>
  );
}
