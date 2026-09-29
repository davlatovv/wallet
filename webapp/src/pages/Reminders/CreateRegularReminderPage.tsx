import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { ErrorState, FormField, PrimaryButton, SubScreen, TextField } from '../../shared/ui';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CreateRegularReminderPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [paymentAmount, setPaymentAmount] = useState('');
  const [firstPaymentDate, setFirstPaymentDate] = useState(todayISO());

  const submit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/reminders/regular', {
        body: {
          name,
          payment_amount: paymentAmount.replace(',', '.'),
          first_payment_date: firstPaymentDate,
        },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminders'] });
      navigate('/reminders');
    },
  });

  const canSubmit = name.trim().length > 0 && Number(paymentAmount.replace(',', '.')) > 0;

  return (
    <SubScreen title="Постоянный расход">
      <div style={{ fontSize: 13, color: 'var(--color-hint)' }}>
        Аренда, подписки — платёж без даты окончания, напоминает каждый месяц.
      </div>
      <FormField label="Название">
        <TextField value={name} onChange={setName} placeholder="Аренда квартиры" />
      </FormField>
      <FormField label="Сумма платежа">
        <TextField
          value={paymentAmount}
          onChange={(v) => setPaymentAmount(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Первый платёж">
        <TextField type="date" value={firstPaymentDate} onChange={setFirstPaymentDate} />
      </FormField>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && submit.mutate()}>
        {submit.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      {submit.isError && (
        <ErrorState message="Не удалось создать напоминание" onRetry={() => submit.mutate()} />
      )}
    </SubScreen>
  );
}
