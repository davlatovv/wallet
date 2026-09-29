import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import {
  Card,
  ErrorState,
  FormField,
  PrimaryButton,
  SegmentedControl,
  SubScreen,
  TextField,
} from '../../shared/ui';
import { formatMoney } from '../../shared/ui/formatMoney';

type PaymentType = 'annuity' | 'differential';

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CreateCreditReminderPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [totalAmount, setTotalAmount] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [monthsTotal, setMonthsTotal] = useState('');
  const [paymentType, setPaymentType] = useState<PaymentType>('annuity');
  const [firstPaymentDate, setFirstPaymentDate] = useState(todayISO());

  const months = Number(monthsTotal);
  const rate = Number(interestRate.replace(',', '.'));
  const amount = Number(totalAmount.replace(',', '.'));
  const previewReady = amount > 0 && interestRate.length > 0 && rate >= 0 && Number.isInteger(months) && months >= 1;
  const canSubmit = name.trim().length > 0 && previewReady;

  const preview = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/reminders/credit/preview', {
        body: {
          total_amount: totalAmount.replace(',', '.'),
          interest_rate: interestRate.replace(',', '.'),
          months_total: months,
          payment_type: paymentType,
        },
      });
      if (error) throw error;
      return data;
    },
  });

  const submit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/reminders/credit', {
        body: {
          name,
          total_amount: totalAmount.replace(',', '.'),
          interest_rate: interestRate.replace(',', '.'),
          months_total: months,
          payment_type: paymentType,
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

  return (
    <SubScreen title="Кредит">
      <FormField label="Название">
        <TextField value={name} onChange={setName} placeholder="Автокредит" />
      </FormField>
      <FormField label="Сумма кредита">
        <TextField
          value={totalAmount}
          onChange={(v) => setTotalAmount(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Ставка, % годовых">
        <TextField
          value={interestRate}
          onChange={(v) => setInterestRate(v.replace(/[^0-9.,]/g, ''))}
          placeholder="0"
          inputMode="decimal"
        />
      </FormField>
      <FormField label="Срок, месяцев">
        <TextField
          value={monthsTotal}
          onChange={(v) => setMonthsTotal(v.replace(/[^0-9]/g, ''))}
          placeholder="12"
          inputMode="numeric"
        />
      </FormField>
      <FormField label="Тип платежа">
        <SegmentedControl
          value={paymentType}
          onChange={setPaymentType}
          options={[
            { value: 'annuity', label: 'Аннуитетный' },
            { value: 'differential', label: 'Дифференцированный' },
          ]}
        />
      </FormField>
      <FormField label="Первый платёж">
        <TextField type="date" value={firstPaymentDate} onChange={setFirstPaymentDate} />
      </FormField>

      <PrimaryButton
        variant="outline"
        onClick={() => previewReady && preview.mutate()}
      >
        {preview.isPending ? t.common.loading : 'Показать график платежей'}
      </PrimaryButton>

      {preview.isError && (
        <ErrorState message="Не удалось рассчитать график" onRetry={() => preview.mutate()} />
      )}

      {preview.data && (
        <>
          <Card>
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>Первый платёж</div>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{formatMoney(preview.data.first_payment)}</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>Всего выплат</div>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{formatMoney(preview.data.total_payment)}</div>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>Переплата</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-expense)' }}>
                  {formatMoney(preview.data.overpayment)}
                </div>
              </div>
            </div>
          </Card>
          <Card padding="10px 12px">
            <div style={{ display: 'flex', fontSize: 11, color: 'var(--color-hint)', padding: '0 4px 6px' }}>
              <div style={{ width: 34 }}>Мес.</div>
              <div style={{ flex: 1, textAlign: 'right' }}>Платёж</div>
              <div style={{ flex: 1, textAlign: 'right' }}>Проценты</div>
              <div style={{ flex: 1, textAlign: 'right' }}>Остаток</div>
            </div>
            {preview.data.schedule.slice(0, 6).map((row, i) => (
              <div
                key={row.month}
                style={{
                  display: 'flex',
                  padding: '8px 4px',
                  fontSize: 13,
                  borderBottom:
                    i < Math.min(5, preview.data!.schedule.length - 1)
                      ? '1px solid var(--color-separator)'
                      : 'none',
                }}
              >
                <div style={{ width: 34 }}>{row.month}</div>
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
          {preview.data.schedule.length > 6 && (
            <div style={{ textAlign: 'center', fontSize: 12, color: 'var(--color-hint)' }}>
              … ещё {preview.data.schedule.length - 6} платежей
            </div>
          )}
        </>
      )}

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
