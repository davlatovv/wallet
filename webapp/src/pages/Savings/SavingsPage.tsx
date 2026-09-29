import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { Card, EmptyState, ErrorState, ProgressBar, SubScreen } from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

export function SavingsPage() {
  const query = useQuery({
    queryKey: ['savings'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/savings');
      if (error) throw error;
      return data;
    },
  });

  return (
    <SubScreen title={t.more.savings}>
      {query.isPending && <EmptyState title={t.common.loading} />}
      {query.isError && <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />}
      {query.data && query.data.length === 0 && (
        <EmptyState title="Нет целей" note="Создайте копилку для крупной покупки" />
      )}
      {query.data?.map((goal) => (
        <Card key={goal.id}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 12,
                background: 'var(--color-bg-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 18,
              }}
            >
              🏦
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 600 }}>{goal.name}</div>
              {goal.deadline && (
                <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>Цель к {goal.deadline}</div>
              )}
            </div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-link)' }}>
              {goal.progress_percent}%
            </div>
          </div>
          <ProgressBar percent={goal.progress_percent} />
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              fontSize: 13,
              color: 'var(--color-hint)',
              margin: '8px 0 12px',
            }}
          >
            <div>{formatMoney(goal.current_amount)}</div>
            <div>из {formatMoney(goal.target_amount)}</div>
          </div>
        </Card>
      ))}
    </SubScreen>
  );
}
