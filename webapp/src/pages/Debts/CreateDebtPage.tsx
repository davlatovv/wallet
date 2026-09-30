import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { ErrorState, FormField, PrimaryButton, SegmentedControl, SubScreen, TextField } from '../../shared/ui';

type DebtType = 'i_owe' | 'owed_to_me';

export function CreateDebtPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [counterparty, setCounterparty] = useState('');
  const [amount, setAmount] = useState('');
  const [debtType, setDebtType] = useState<DebtType>('i_owe');
  const [dueDate, setDueDate] = useState('');
  const [description, setDescription] = useState('');

  const submit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/debts', {
        body: {
          counterparty,
          amount: amount.replace(',', '.'),
          debt_type: debtType,
          due_date: dueDate || null,
          description: description || null,
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['debts'] });
      navigate(-1);
    },
  });

  const canSubmit = counterparty.trim().length > 0 && Number(amount.replace(',', '.')) > 0;

  return (
    <SubScreen title="Новый долг">
      <FormField label="Тип">
        <SegmentedControl
          value={debtType}
          onChange={setDebtType}
          options={[
            { value: 'i_owe', label: 'Я должен' },
            { value: 'owed_to_me', label: 'Мне должны' },
          ]}
        />
      </FormField>
      <FormField label="Имя">
        <TextField value={counterparty} onChange={setCounterparty} placeholder="Алишер" />
      </FormField>
      <FormField label="Сумма">
        <TextField
          value={amount}
          onChange={(v) => setAmount(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Срок (необязательно)">
        <TextField type="date" value={dueDate} onChange={setDueDate} />
      </FormField>
      <FormField label="Заметка (необязательно)">
        <TextField value={description} onChange={setDescription} />
      </FormField>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && submit.mutate()}>
        {submit.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      {submit.isError && (
        <ErrorState message="Не удалось добавить долг" onRetry={() => submit.mutate()} />
      )}
    </SubScreen>
  );
}
