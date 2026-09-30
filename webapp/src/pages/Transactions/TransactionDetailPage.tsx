import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { confirmDialog } from '../../shared/telegram/confirmDialog';
import type { components } from '../../shared/api/schema';
import {
  EmptyState,
  ErrorState,
  FormField,
  PrimaryButton,
  SegmentedControl,
  SubScreen,
  TextField,
} from '../../shared/ui';

type Currency = 'UZS' | 'USD' | 'CASH';
type Transaction = components['schemas']['TransactionResponse'];

/**
 * There's no GET /transactions/{id} on the backend (only list/create/patch/
 * delete), so this re-fetches a page of the list and finds the item by id
 * — simple and correct for a personal-finance data volume, if not the most
 * efficient possible round trip.
 */
export function TransactionDetailPage() {
  const { transactionId } = useParams<{ transactionId: string }>();
  const id = Number(transactionId);

  const query = useQuery({
    queryKey: ['transactions', { limit: 100 }],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/transactions', {
        params: { query: { limit: 100 } },
      });
      if (error) throw error;
      return data;
    },
  });
  const tx = query.data?.items.find((item) => item.id === id);

  if (query.isPending) {
    return (
      <SubScreen title="Операция">
        <EmptyState title={t.common.loading} />
      </SubScreen>
    );
  }
  if (query.isError) {
    return (
      <SubScreen title="Операция">
        <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />
      </SubScreen>
    );
  }
  if (!tx) {
    return (
      <SubScreen title="Операция">
        <EmptyState title="Операция не найдена" />
      </SubScreen>
    );
  }

  if (tx.transaction_type === 'savings') {
    return (
      <SubScreen title={tx.category_name ?? 'Операция'}>
        <EmptyState
          title="Пополнение копилки"
          note="Такие операции изменяются через раздел «Копилка», а не напрямую."
        />
      </SubScreen>
    );
  }

  // Keyed by id: a fresh mount per transaction means the form's local state
  // can be initialized straight from `tx` (no effect needed to sync it in
  // after the async fetch resolves — see the oxlint set-state-in-effect
  // warning this replaced).
  return <TransactionEditForm key={tx.id} tx={tx} />;
}

function TransactionEditForm({ tx }: { tx: Transaction }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [amount, setAmount] = useState(tx.original_amount ?? tx.amount);
  const [currency, setCurrency] = useState<Currency>(tx.currency as Currency);
  const [note, setNote] = useState(tx.note ?? '');

  const invalidateAfterChange = () => {
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
    queryClient.invalidateQueries({ queryKey: ['balance'] });
    queryClient.invalidateQueries({ queryKey: ['report'] });
  };

  const save = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.PATCH('/api/v1/transactions/{transaction_id}', {
        params: { path: { transaction_id: tx.id } },
        body: { amount: amount.replace(',', '.'), currency, note: note || null },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      invalidateAfterChange();
      navigate(-1);
    },
  });

  const remove = useMutation({
    mutationFn: async () => {
      const { error } = await apiClient.DELETE('/api/v1/transactions/{transaction_id}', {
        params: { path: { transaction_id: tx.id } },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      invalidateAfterChange();
      navigate(-1);
    },
  });

  const canSubmit = amount.length > 0 && Number(amount.replace(',', '.')) > 0;

  return (
    <SubScreen title={tx.category_name ?? 'Операция'}>
      <FormField label="Сумма">
        <TextField
          value={amount}
          onChange={(v) => setAmount(v.replace(/[^0-9.,]/g, ''))}
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Валюта">
        <SegmentedControl
          value={currency}
          onChange={setCurrency}
          options={[
            { value: 'UZS', label: 'UZS' },
            { value: 'USD', label: 'USD' },
            { value: 'CASH', label: 'Наличные' },
          ]}
        />
      </FormField>
      <FormField label="Заметка">
        <TextField value={note} onChange={setNote} placeholder="Заметка (необязательно)" />
      </FormField>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && save.mutate()}>
        {save.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      <PrimaryButton
        variant="danger"
        onClick={() => confirmDialog('Удалить операцию?').then((ok) => ok && remove.mutate())}
      >
        {remove.isPending ? t.common.loading : t.common.delete}
      </PrimaryButton>
      {save.isError && (
        <ErrorState message="Не удалось сохранить изменения" onRetry={() => save.mutate()} />
      )}
      {remove.isError && (
        <ErrorState message="Не удалось удалить операцию" onRetry={() => remove.mutate()} />
      )}
    </SubScreen>
  );
}
