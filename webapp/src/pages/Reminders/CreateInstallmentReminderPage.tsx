import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { ErrorState, FormField, PrimaryButton, SubScreen, TextField } from '../../shared/ui';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CreateInstallmentReminderPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [totalAmount, setTotalAmount] = useState('');
  const [monthlyPayment, setMonthlyPayment] = useState('');
  const [monthsTotal, setMonthsTotal] = useState('');
  const [firstPaymentDate, setFirstPaymentDate] = useState(todayISO());

  const submit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/reminders/installment', {
        body: {
          name,
          total_amount: totalAmount.replace(',', '.'),
          monthly_payment: monthlyPayment.replace(',', '.'),
          months_total: Number(monthsTotal),
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

  const months = Number(monthsTotal);
  const canSubmit =
    name.trim().length > 0 &&
    Number(totalAmount.replace(',', '.')) > 0 &&
    Number(monthlyPayment.replace(',', '.')) > 0 &&
    Number.isInteger(months) &&
    months >= 1;

  return (
    <SubScreen title="Рассрочка">
      <div style={{ fontSize: 13, color: 'var(--color-hint)' }}>
        Фиксированный ежемесячный платёж на заданное число месяцев, без процентов.
      </div>
      <FormField label="Название">
        <TextField value={name} onChange={setName} placeholder="iPhone 16" />
      </FormField>
      <FormField label="Общая сумма">
        <TextField
          value={totalAmount}
          onChange={(v) => setTotalAmount(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Ежемесячный платёж">
        <TextField
          value={monthlyPayment}
          onChange={(v) => setMonthlyPayment(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Количество месяцев">
        <TextField
          value={monthsTotal}
          onChange={(v) => setMonthsTotal(v.replace(/[^0-9]/g, ''))}
          placeholder="12"
          inputMode="numeric"
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
