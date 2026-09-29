import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { Card, EmptyState, ErrorState, ListItem, SubScreen } from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  active: { text: 'Активен', color: 'var(--color-link)' },
  settled: { text: 'Оплачен', color: 'var(--color-income)' },
  overdue: { text: 'Просрочен', color: 'var(--color-destructive)' },
};

export function DebtsPage() {
  const query = useQuery({
    queryKey: ['debts'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/debts');
      if (error) throw error;
      return data;
    },
  });

  const owedToMe = query.data?.filter((d) => d.debt_type === 'owed_to_me') ?? [];
  const iOwe = query.data?.filter((d) => d.debt_type === 'i_owe') ?? [];

  const renderGroup = (title: string, items: typeof owedToMe) =>
    items.length > 0 && (
      <div key={title} style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-hint)', textTransform: 'uppercase' }}>
          {title}
        </div>
        <Card padding="4px 12px">
          {items.map((debt, i) => {
            const status = STATUS_LABEL[debt.status] ?? { text: debt.status, color: 'var(--color-hint)' };
            return (
              <ListItem
                key={debt.id}
                border={i < items.length - 1}
                left={
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 600 }}>{debt.counterparty}</div>
                    {debt.due_date && (
                      <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>До {debt.due_date}</div>
                    )}
                  </div>
                }
                right={
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 600, fontSize: 15 }}>{formatMoney(debt.amount)}</div>
                    <div style={{ fontSize: 11, color: status.color, fontWeight: 600 }}>{status.text}</div>
                  </div>
                }
              />
            );
          })}
        </Card>
      </div>
    );

  return (
    <SubScreen title={t.more.debts}>
      {query.isPending && <EmptyState title={t.common.loading} />}
      {query.isError && <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />}
      {query.data && query.data.length === 0 && <EmptyState title="Нет долгов" />}
      {renderGroup('Мне должны', owedToMe)}
      {renderGroup('Я должен', iOwe)}
    </SubScreen>
  );
}
