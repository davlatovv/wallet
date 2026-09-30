import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { ErrorState, FormField, PrimaryButton, SubScreen, TextField } from '../../shared/ui';

export function CreateSavingsGoalPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [deadline, setDeadline] = useState('');
  const [description, setDescription] = useState('');

  const submit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/savings', {
        body: {
          name,
          target_amount: targetAmount.replace(',', '.'),
          deadline: deadline || null,
          description: description || null,
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['savings'] });
      navigate(-1);
    },
  });

  const canSubmit = name.trim().length > 0 && Number(targetAmount.replace(',', '.')) > 0;

  return (
    <SubScreen title="Новая цель">
      <FormField label="Название">
        <TextField value={name} onChange={setName} placeholder="Отпуск" />
      </FormField>
      <FormField label="Целевая сумма">
        <TextField
          value={targetAmount}
          onChange={(v) => setTargetAmount(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Срок (необязательно)">
        <TextField type="date" value={deadline} onChange={setDeadline} />
      </FormField>
      <FormField label="Заметка (необязательно)">
        <TextField value={description} onChange={setDescription} />
      </FormField>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && submit.mutate()}>
        {submit.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      {submit.isError && (
        <ErrorState message="Не удалось создать цель" onRetry={() => submit.mutate()} />
      )}
    </SubScreen>
  );
}
