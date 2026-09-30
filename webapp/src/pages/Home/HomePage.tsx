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
  PrimaryButton,
  Screen,
  ScreenBody,
  StatTile,
  TabBar,
} from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

function useBalance() {
  return useQuery({
    queryKey: ['balance'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/balance');
      if (error) throw error;
      return data;
    },
  });
}

function useRecentTransactions() {
  return useQuery({
    queryKey: ['transactions', { limit: 5 }],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/transactions', {
        params: { query: { limit: 5 } },
      });
      if (error) throw error;
      return data;
    },
  });
}

export function HomePage() {
  const balance = useBalance();
  const recent = useRecentTransactions();

  return (
    <Screen>
      <Header title={t.home.title} />
      <ScreenBody>
        {balance.isPending && <EmptyState title={t.common.loading} />}
        {balance.isError && (
          <ErrorState message={t.errors.loadFailed} onRetry={() => balance.refetch()} />
        )}
        {balance.data && (
          <Card>
            <div style={{ fontSize: 13, color: 'var(--color-hint)', marginBottom: 4 }}>
              {t.home.totalBalance}
            </div>
            <div style={{ fontSize: 32, fontWeight: 700, letterSpacing: -0.5, marginBottom: 16 }}>
              {formatMoney(balance.data.total_balance)}{' '}
              <span style={{ fontSize: 16, color: 'var(--color-hint)', fontWeight: 600 }}>
                {t.common.currencyUZS}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <StatTile label={t.home.cash} value={formatMoney(balance.data.cash_balance)} />
              <StatTile label={t.home.card} value={formatMoney(balance.data.card_balance)} />
              <StatTile label={t.home.usd} value={formatMoney(balance.data.currency_balance)} />
            </div>
          </Card>
        )}

        <div style={{ display: 'flex', gap: 10 }}>
          <PrimaryButton href="/add-transaction">− {t.home.expense}</PrimaryButton>
          <PrimaryButton href="/add-transaction">+ {t.home.income}</PrimaryButton>
        </div>

        {balance.data && (
          <Card>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>{t.home.thisMonth}</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <StatTile
                label={t.home.incomeLabel}
                value={formatMoney(balance.data.total_income)}
                color="var(--color-income)"
              />
              <StatTile
                label={t.home.expenseLabel}
                value={formatMoney(balance.data.total_expense)}
                color="var(--color-expense)"
              />
              <StatTile label={t.home.balanceLabel} value={formatMoney(balance.data.total_balance)} />
            </div>
          </Card>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>{t.home.recentTransactions}</div>
          <a href="/transactions" style={{ fontSize: 14 }}>
            {t.home.viewAll} →
          </a>
        </div>

        {recent.isPending && <EmptyState title={t.common.loading} />}
        {recent.data && recent.data.items.length === 0 && (
          <EmptyState title="Пока нет операций" note="Добавьте первый расход или доход" />
        )}
        {recent.data && recent.data.items.length > 0 && (
          <Card padding="4px 12px">
            {recent.data.items.map((tx, i) => (
              <ListItem
                key={tx.id}
                href={`/transactions/${tx.id}`}
                border={i < recent.data.items.length - 1}
                left={
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                    <IconAvatar>{tx.transaction_type === 'income' ? '💼' : '🧾'}</IconAvatar>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 15 }}>{tx.category_name ?? '—'}</div>
                      {tx.note && (
                        <div
                          style={{
                            fontSize: 12,
                            color: 'var(--color-hint)',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {tx.note}
                        </div>
                      )}
                    </div>
                  </div>
                }
                right={
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
