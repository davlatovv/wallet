import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { EmptyState, ErrorState, FormField, PrimaryButton, ProgressBar, SubScreen, TextField } from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

/** No GET /savings/{id} on the backend — find it in the full list. */
export function DepositPage() {
  const { goalId } = useParams<{ goalId: string }>();
  const id = Number(goalId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ['savings'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/savings');
      if (error) throw error;
      return data;
    },
  });
  const goal = query.data?.find((item) => item.id === id);

  const [amount, setAmount] = useState('');

  const deposit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/savings/{goal_id}/deposit', {
        params: { path: { goal_id: id } },
        body: { amount: amount.replace(',', '.') },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savings'] });
      queryClient.invalidateQueries({ queryKey: ['balance'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      navigate(-1);
    },
  });

  if (query.isPending) {
    return (
      <SubScreen title="Пополнить">
        <EmptyState title={t.common.loading} />
      </SubScreen>
    );
  }
  if (query.isError) {
    return (
      <SubScreen title="Пополнить">
        <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />
      </SubScreen>
    );
  }
  if (!goal) {
    return (
      <SubScreen title="Пополнить">
        <EmptyState title="Цель не найдена" />
      </SubScreen>
    );
  }

  const canSubmit = Number(amount.replace(',', '.')) > 0;

  return (
    <SubScreen title={goal.name}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: 'var(--color-hint)' }}>
        <div>{formatMoney(goal.current_amount)}</div>
        <div>из {formatMoney(goal.target_amount)}</div>
      </div>
      <ProgressBar percent={goal.progress_percent} />

      <FormField label="Сумма пополнения">
        <TextField
          value={amount}
          onChange={(v) => setAmount(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>
        Сумма спишется с карточного счёта и запишется как операция.
      </div>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && deposit.mutate()}>
        {deposit.isPending ? t.common.loading : 'Пополнить'}
      </PrimaryButton>
      {deposit.isError && (
        <ErrorState message="Не удалось пополнить копилку" onRetry={() => deposit.mutate()} />
      )}
    </SubScreen>
  );
}
