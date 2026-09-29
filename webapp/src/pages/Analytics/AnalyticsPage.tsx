import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import {
  Card,
  EmptyState,
  ErrorState,
  Header,
  ProgressBar,
  Screen,
  ScreenBody,
  StatTile,
  TabBar,
} from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

type Period = 'day' | 'week' | 'month' | 'year';

const PERIODS: { key: Period; label: string }[] = [
  { key: 'day', label: 'День' },
  { key: 'week', label: 'Неделя' },
  { key: 'month', label: 'Месяц' },
  { key: 'year', label: 'Год' },
];

const BAR_COLORS = ['var(--color-expense)', 'var(--color-link)', 'var(--color-warning)', 'var(--color-hint)'];

export function AnalyticsPage() {
  const [period, setPeriod] = useState<Period>('month');

  const query = useQuery({
    queryKey: ['report', period],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/analytics/report', {
        params: { query: { period } },
      });
      if (error) throw error;
      return data;
    },
  });

  return (
    <Screen>
      <Header title={t.tabs.analytics} />
      <ScreenBody>
        <div style={{ display: 'flex', background: 'var(--color-bg-secondary)', borderRadius: 12, padding: 3 }}>
          {PERIODS.map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => setPeriod(p.key)}
              style={{
                flex: 1,
                textAlign: 'center',
                padding: '9px 0',
                borderRadius: 9,
                fontSize: 13,
                border: 'none',
                cursor: 'pointer',
                background: period === p.key ? 'var(--color-link)' : 'transparent',
                color: period === p.key ? 'var(--color-button-text)' : 'var(--color-text)',
                fontWeight: period === p.key ? 600 : 400,
              }}
            >
              {p.label}
            </button>
          ))}
        </div>

        {query.isPending && <EmptyState title={t.common.loading} />}
        {query.isError && (
          <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />
        )}

        {query.data && (
          <>
            <Card>
              <div style={{ display: 'flex', gap: 8 }}>
                <StatTile
                  label={t.home.incomeLabel}
                  value={formatMoney(query.data.total_income)}
                  color="var(--color-income)"
                />
                <StatTile
                  label={t.home.expenseLabel}
                  value={formatMoney(query.data.total_expense)}
                  color="var(--color-expense)"
                />
                <StatTile label={t.home.balanceLabel} value={formatMoney(query.data.balance)} />
              </div>
            </Card>

            <div style={{ fontSize: 15, fontWeight: 600 }}>Расходы по категориям</div>
            {query.data.expense_by_category.length === 0 && (
              <EmptyState title="Нет расходов за этот период" />
            )}
            {query.data.expense_by_category.length > 0 && (
              <Card padding="6px 16px">
                {query.data.expense_by_category.map((row, i) => (
                  <div
                    key={row.category_id}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 6,
                      padding: '10px 0',
                      borderBottom:
                        i < query.data.expense_by_category.length - 1
                          ? '1px solid var(--color-separator)'
                          : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                      <div>{row.category_name}</div>
                      <div style={{ color: 'var(--color-hint)' }}>
                        {formatMoney(row.amount)} · {row.percent}%
                      </div>
                    </div>
                    <ProgressBar percent={row.percent} color={BAR_COLORS[i % BAR_COLORS.length]} />
                  </div>
                ))}
              </Card>
            )}
          </>
        )}
      </ScreenBody>
      <TabBar />
    </Screen>
  );
}
