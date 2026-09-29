import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import {
  Card,
  EmptyState,
  ErrorState,
  Header,
  IconAvatar,
  ListItem,
  Screen,
  ScreenBody,
  TabBar,
} from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

const dateFormatter = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});

export function TransactionsPage() {
  const query = useQuery({
    queryKey: ['transactions', { limit: 30 }],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/transactions', {
        params: { query: { limit: 30 } },
      });
      if (error) throw error;
      return data;
    },
  });

  return (
    <Screen>
      <Header title={t.tabs.transactions} />
      <ScreenBody>
        {query.isPending && <EmptyState title={t.common.loading} />}
        {query.isError && (
          <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />
        )}
        {query.data && query.data.items.length === 0 && (
          <EmptyState title="Пока нет операций" note="Добавьте первую запись с главного экрана" />
        )}
        {query.data && query.data.items.length > 0 && (
          <Card padding="4px 12px">
            {query.data.items.map((tx, i) => (
              <ListItem
                key={tx.id}
                border={i < query.data.items.length - 1}
                left={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                    <IconAvatar>{tx.transaction_type === 'income' ? '💼' : '🧾'}</IconAvatar>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 15 }}>{tx.category_name ?? '—'}</div>
                      <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>
                        {dateFormatter.format(new Date(tx.created_at))}
                      </div>
                    </div>
                  </div>
                }
                right={
                  <div style={{ textAlign: 'right' }}>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: 15,
                        color:
                          tx.transaction_type === 'income'
                            ? 'var(--color-income)'
                            : 'var(--color-expense)',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {tx.transaction_type === 'income' ? '+' : '−'}
                      {formatMoney(tx.amount)}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--color-hint)' }}>
                      {tx.account_type === 'cash'
                        ? '💵'
                        : tx.account_type === 'currency'
                          ? '🇺🇸'
                          : '💳'}
                    </div>
                  </div>
                }
              />
            ))}
          </Card>
        )}
      </ScreenBody>
      <TabBar />
    </Screen>
  );
}
