import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { confirmDialog } from '../../shared/telegram/confirmDialog';
import { Card, EmptyState, ErrorState, PrimaryButton, StatTile, SubScreen } from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

const STATUS_LABEL: Record<string, string> = {
  active: 'Активен',
  settled: 'Оплачен',
  overdue: 'Просрочен',
};

/** No GET /debts/{id} on the backend — find it in the full list. */
export function DebtDetailPage() {
  const { debtId } = useParams<{ debtId: string }>();
  const id = Number(debtId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['debts'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/debts');
      if (error) throw error;
      return data;
    },
  });
  const debt = query.data?.find((item) => item.id === id);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['debts'] });

  const settle = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/debts/{debt_id}/settle', {
        params: { path: { debt_id: id } },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: async () => {
      const { error } = await apiClient.DELETE('/api/v1/debts/{debt_id}', {
        params: { path: { debt_id: id } },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      invalidate();
      navigate(-1);
    },
  });

  if (query.isPending) {
    return (
      <SubScreen title="Долг">
        <EmptyState title={t.common.loading} />
      </SubScreen>
    );
  }
  if (query.isError) {
    return (
      <SubScreen title="Долг">
        <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />
      </SubScreen>
    );
  }
  if (!debt) {
    return (
      <SubScreen title="Долг">
        <EmptyState title="Долг не найден" />
      </SubScreen>
    );
  }

  return (
    <SubScreen title={debt.counterparty}>
      <Card>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <StatTile label="Сумма" value={formatMoney(debt.amount)} />
          <StatTile label="Статус" value={STATUS_LABEL[debt.status] ?? debt.status} />
          {debt.due_date && <StatTile label="Срок" value={debt.due_date} />}
        </div>
        {debt.description && (
          <div style={{ fontSize: 13, color: 'var(--color-hint)' }}>{debt.description}</div>
        )}
      </Card>

      <div style={{ flex: 1 }} />
      {debt.status === 'active' && (
        <PrimaryButton onClick={() => settle.mutate()}>
          {settle.isPending ? t.common.loading : 'Отметить оплаченным'}
        </PrimaryButton>
      )}
      <PrimaryButton
        variant="danger"
        onClick={() => confirmDialog('Удалить долг?').then((ok) => ok && remove.mutate())}
      >
        {remove.isPending ? t.common.loading : t.common.delete}
      </PrimaryButton>
      {settle.isError && (
        <ErrorState message="Не удалось отметить долг оплаченным" onRetry={() => settle.mutate()} />
      )}
      {remove.isError && (
        <ErrorState message="Не удалось удалить долг" onRetry={() => remove.mutate()} />
      )}
    </SubScreen>
  );
}
