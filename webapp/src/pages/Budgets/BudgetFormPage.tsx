import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { confirmDialog } from '../../shared/telegram/confirmDialog';
import { ErrorState, FormField, PrimaryButton, SegmentedControl, SubScreen, TextField } from '../../shared/ui';

type Period = 'daily' | 'weekly' | 'monthly';

interface ExistingBudget {
  id: number;
  category_id: number | null;
  period: Period;
  limit_amount: string;
}

const PERIOD_OPTIONS: { value: Period; label: string }[] = [
  { value: 'daily', label: 'День' },
  { value: 'weekly', label: 'Неделя' },
  { value: 'monthly', label: 'Месяц' },
];

/** PUT /budgets upserts by (category, period), so create and edit share one
 * form — editing an existing budget just pre-fills and re-submits. */
export function BudgetFormPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const editing = location.state as ExistingBudget | null;

  const categories = useQuery({
    queryKey: ['categories', 'expense'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/categories', {
        params: { query: { type: 'expense' } },
      });
      if (error) throw error;
      return data;
    },
  });

  const [categoryId, setCategoryId] = useState<number | null>(editing?.category_id ?? null);
  const [period, setPeriod] = useState<Period>(editing?.period ?? 'monthly');
  const [limitAmount, setLimitAmount] = useState(editing?.limit_amount ?? '');

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['budgets'] });

  const submit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.PUT('/api/v1/budgets', {
        body: { category_id: categoryId, period, limit_amount: limitAmount.replace(',', '.') },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      invalidate();
      navigate(-1);
    },
  });

  const remove = useMutation({
    mutationFn: async () => {
      if (!editing) return;
      const { error } = await apiClient.DELETE('/api/v1/budgets/{budget_id}', {
        params: { path: { budget_id: editing.id } },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      invalidate();
      navigate(-1);
    },
  });

  const canSubmit = Number(limitAmount.replace(',', '.')) > 0;

  return (
    <SubScreen title={editing ? 'Изменить бюджет' : 'Новый бюджет'}>
      <FormField label="Категория">
        <select
          value={categoryId ?? ''}
          onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
          style={{
            background: 'var(--color-bg)',
            border: 'none',
            borderRadius: 'var(--radius-control)',
            padding: '12px 14px',
            fontSize: 15,
            color: 'var(--color-text)',
            width: '100%',
          }}
        >
          <option value="">Общий (все категории)</option>
          {categories.data?.map((cat) => (
            <option key={cat.id} value={cat.id}>
              {cat.icon ? `${cat.icon} ` : ''}
              {cat.name}
            </option>
          ))}
        </select>
      </FormField>
      <FormField label="Период">
        <SegmentedControl value={period} onChange={setPeriod} options={PERIOD_OPTIONS} />
      </FormField>
      <FormField label="Лимит">
        <TextField
          value={limitAmount}
          onChange={(v) => setLimitAmount(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && submit.mutate()}>
        {submit.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      {editing && (
        <PrimaryButton
          variant="danger"
          onClick={() => confirmDialog('Удалить бюджет?').then((ok) => ok && remove.mutate())}
        >
          {remove.isPending ? t.common.loading : t.common.delete}
        </PrimaryButton>
      )}
      {submit.isError && (
        <ErrorState message="Не удалось сохранить бюджет" onRetry={() => submit.mutate()} />
      )}
      {remove.isError && (
        <ErrorState message="Не удалось удалить бюджет" onRetry={() => remove.mutate()} />
      )}
    </SubScreen>
  );
}
