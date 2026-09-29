import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import {
  Card,
  EmptyState,
  ErrorState,
  IconAvatar,
  ListItem,
  PrimaryButton,
  ProgressBar,
  SubScreen,
} from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

const TYPE_ICON: Record<string, string> = {
  credit: '💳',
  installment: '📆',
  education: '📚',
  regular: '🔄',
};

const TYPE_LABEL: Record<string, string> = {
  credit: 'Кредит',
  installment: 'Рассрочка',
  education: 'Учёба',
  regular: 'Постоянный',
};

export function RemindersListPage() {
  const query = useQuery({
    queryKey: ['reminders'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/reminders');
      if (error) throw error;
      return data;
    },
  });

  return (
    <SubScreen title={t.more.reminders}>
      {query.isPending && <EmptyState title={t.common.loading} />}
      {query.isError && <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />}
      {query.data && query.data.length === 0 && <EmptyState title="Нет напоминаний" />}
      {query.data && query.data.length > 0 && (
        <Card padding="4px 12px">
          {query.data.map((reminder, i) => (
            <ListItem
              key={reminder.id}
              href={`/reminders/${reminder.id}`}
              border={i < query.data.length - 1}
              left={
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <IconAvatar>{TYPE_ICON[reminder.reminder_type] ?? '🔔'}</IconAvatar>
                  <div>
                    <div style={{ fontSize: 15 }}>{reminder.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>
                      {TYPE_LABEL[reminder.reminder_type]} · до {reminder.next_payment_date}
                    </div>
                    {reminder.progress_percent != null && (
                      <div style={{ width: 60, marginTop: 6 }}>
                        <ProgressBar percent={reminder.progress_percent} />
                      </div>
                    )}
                  </div>
                </div>
              }
              right={<div style={{ fontWeight: 600, fontSize: 15 }}>{formatMoney(reminder.payment_amount)}</div>}
            />
          ))}
        </Card>
      )}
      <PrimaryButton href="/reminders/new" variant="outline">
        + Новое напоминание
      </PrimaryButton>
    </SubScreen>
  );
}
