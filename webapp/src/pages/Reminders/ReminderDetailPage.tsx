import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { Card, EmptyState, ErrorState, PrimaryButton, ProgressBar, StatTile, SubScreen } from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

export function ReminderDetailPage() {
  const { reminderId } = useParams<{ reminderId: string }>();
  const id = Number(reminderId);
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['reminder', id],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/reminders/{reminder_id}', {
        params: { path: { reminder_id: id } },
      });
      if (error) throw error;
      return data;
    },
    enabled: Number.isFinite(id),
  });

  const recordPayment = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/reminders/{reminder_id}/payments', {
        params: { path: { reminder_id: id } },
        body: {},
      });
      if (error) throw error;
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['reminder', id], data);
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
    },
  });

  if (query.isPending) {
    return (
      <SubScreen title="…">
        <EmptyState title={t.common.loading} />
      </SubScreen>
    );
  }
  if (query.isError || !query.data) {
    return (
      <SubScreen title="…">
        <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />
      </SubScreen>
    );
  }

  const r = query.data;

  return (
    <SubScreen title={r.name}>
      <Card>
        <div style={{ fontSize: 12, color: 'var(--color-hint)', marginBottom: 4 }}>
          {r.status === 'completed' ? 'Завершено' : 'Активно'}
          {r.payment_type && ` · ${r.payment_type === 'annuity' ? 'Аннуитетный' : 'Дифференцированный'}`}
          {r.interest_rate && `, ${r.interest_rate}% годовых`}
        </div>
        <div style={{ display: 'flex', gap: 8, margin: '10px 0 14px' }}>
          {r.total_amount && <StatTile label="Сумма" value={formatMoney(r.total_amount)} />}
          <StatTile label="Оплачено" value={formatMoney(r.paid_amount)} color="var(--color-income)" />
          {r.remaining_amount && (
            <StatTile label="Остаток" value={formatMoney(r.remaining_amount)} color="var(--color-expense)" />
          )}
        </div>
        {r.progress_percent != null && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--color-hint)', marginBottom: 6 }}>
              <div>
                Оплачено {r.months_paid}
                {r.months_total ? `/${r.months_total}` : ''} мес.
              </div>
              <div>{r.progress_percent}%</div>
            </div>
            <ProgressBar percent={r.progress_percent} />
          </>
        )}
      </Card>

      {r.payment_schedule && r.payment_schedule.length > 0 && (
        <>
          <div style={{ fontSize: 15, fontWeight: 600 }}>График платежей</div>
          <Card padding="10px 12px">
            <div style={{ display: 'flex', fontSize: 11, color: 'var(--color-hint)', padding: '0 4px 6px' }}>
              <div style={{ width: 34 }}>Мес.</div>
              <div style={{ flex: 1, textAlign: 'right' }}>Платёж</div>
              <div style={{ flex: 1, textAlign: 'right' }}>Проценты</div>
              <div style={{ flex: 1, textAlign: 'right' }}>Остаток</div>
            </div>
            {r.payment_schedule.slice(0, 6).map((row, i) => (
              <div
                key={row.month}
                style={{
                  display: 'flex',
                  padding: '8px 4px',
                  fontSize: 13,
                  borderBottom:
                    i < Math.min(5, r.payment_schedule!.length - 1) ? '1px solid var(--color-separator)' : 'none',
                }}
              >
                <div style={{ width: 34 }}>{row.month <= r.months_paid ? '✅' : '⬜️'} {row.month}</div>
                <div style={{ flex: 1, textAlign: 'right' }}>{formatMoney(row.payment)}</div>
                <div style={{ flex: 1, textAlign: 'right', color: 'var(--color-hint)' }}>
                  {formatMoney(row.interest_part)}
                </div>
                <div style={{ flex: 1, textAlign: 'right', color: 'var(--color-hint)' }}>
                  {formatMoney(row.balance)}
                </div>
              </div>
            ))}
          </Card>
          {r.payment_schedule.length > 6 && (
            <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--color-hint)' }}>
              … ещё {r.payment_schedule.length - 6} платежей
            </div>
          )}
        </>
      )}

      {r.status === 'active' && (
        <PrimaryButton onClick={() => recordPayment.mutate()}>
          {recordPayment.isPending
            ? t.common.loading
            : `Записать платёж — ${formatMoney(r.payment_amount)}`}
        </PrimaryButton>
      )}
      {recordPayment.isError && (
        <ErrorState message="Не удалось записать платёж" onRetry={() => recordPayment.mutate()} />
      )}
    </SubScreen>
  );
}
