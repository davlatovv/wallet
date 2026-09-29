import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { Card, EmptyState, ErrorState, IconAvatar, ProgressBar, SubScreen } from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

const PERIOD_LABELS: Record<string, string> = {
  daily: 'Ежедневно',
  weekly: 'Еженедельно',
  monthly: 'Ежемесячно',
};

export function BudgetsPage() {
  const query = useQuery({
    queryKey: ['budgets'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/budgets');
      if (error) throw error;
      return data;
    },
  });

  return (
    <SubScreen title={t.more.budgets}>
      {query.isPending && <EmptyState title={t.common.loading} />}
      {query.isError && <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />}
      {query.data && query.data.length === 0 && (
        <EmptyState title="Нет бюджетов" note="Создайте бюджет, чтобы отслеживать траты" />
      )}
      {query.data?.map((budget) => {
        const color = budget.is_critical
          ? 'var(--color-destructive)'
          : budget.is_warning
            ? 'var(--color-warning)'
            : 'var(--color-income)';
        return (
          <Card key={budget.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <IconAvatar>🎯</IconAvatar>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600 }}>
                    {budget.category_name ?? 'Общий бюджет'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>
                    {PERIOD_LABELS[budget.period] ?? budget.period}
                  </div>
                </div>
              </div>
              <div style={{ fontSize: 13, fontWeight: 700, color }}>
                {Math.round(budget.used_ratio * 100)}%
              </div>
            </div>
            <ProgressBar percent={budget.used_ratio * 100} color={color} />
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 13,
                color: 'var(--color-hint)',
                marginTop: 8,
              }}
            >
              <div>{formatMoney(budget.spent)} потрачено</div>
              <div>из {formatMoney(budget.limit_amount)}</div>
            </div>
          </Card>
        );
      })}
    </SubScreen>
  );
}
