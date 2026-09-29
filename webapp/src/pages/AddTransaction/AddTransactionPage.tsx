import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { EmptyState, ErrorState, PrimaryButton, SubScreen } from '../../shared/ui';

type Kind = 'expense' | 'income';
type Currency = 'UZS' | 'USD' | 'CASH';

export function AddTransactionPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [kind, setKind] = useState<Kind>('expense');
  const [amount, setAmount] = useState('');
  const [currency, setCurrency] = useState<Currency>('UZS');
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [note, setNote] = useState('');

  const categories = useQuery({
    queryKey: ['categories', kind],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/categories', {
        params: { query: { type: kind } },
      });
      if (error) throw error;
      return data;
    },
  });

  const submit = useMutation({
    mutationFn: async () => {
      const path = kind === 'expense' ? '/api/v1/transactions/expense' : '/api/v1/transactions/income';
      const { data, error } = await apiClient.POST(path, {
        body: { amount: amount.replace(',', '.'), currency, category_id: categoryId, note: note || null },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['balance'] });
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
      queryClient.invalidateQueries({ queryKey: ['report'] });
      navigate(-1);
    },
  });

  const parsedAmount = Number(amount.replace(',', '.'));
  const canSubmit = amount.length > 0 && parsedAmount > 0 && !submit.isPending;

  return (
    <SubScreen title="Добавить операцию">
      <div style={{ display: 'flex', background: 'var(--color-bg-secondary)', borderRadius: 12, padding: 3 }}>
        {(['expense', 'income'] as const).map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => {
              setKind(k);
              setCategoryId(null);
            }}
            style={{
              flex: 1,
              textAlign: 'center',
              padding: '10px 0',
              borderRadius: 10,
              fontSize: 14,
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              background: kind === k ? (k === 'expense' ? 'var(--color-expense)' : 'var(--color-income)') : 'transparent',
              color: kind === k ? '#fff' : 'var(--color-text)',
            }}
          >
            {k === 'expense' ? t.home.expense : t.home.income}
          </button>
        ))}
      </div>

      <div style={{ textAlign: 'center', padding: '8px 0' }}>
        <input
          type="text"
          inputMode="decimal"
          placeholder="0"
          value={amount}
          onChange={(e) => setAmount(e.target.value.replace(/[^0-9.,]/g, ''))}
          style={{
            border: 'none',
            background: 'none',
            fontSize: 40,
            fontWeight: 700,
            textAlign: 'center',
            width: '100%',
            color: 'var(--color-text)',
            outline: 'none',
          }}
        />
        <div style={{ fontSize: 13, color: 'var(--color-hint)' }}>Введите сумму</div>
      </div>

      <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
        {(['UZS', 'USD', 'CASH'] as const).map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCurrency(c)}
            style={{
              padding: '7px 14px',
              borderRadius: 16,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              border: currency === c ? 'none' : '1px solid var(--color-separator)',
              background: currency === c ? 'var(--color-link)' : 'var(--color-bg)',
              color: currency === c ? '#fff' : 'var(--color-text)',
            }}
          >
            {c === 'UZS' ? 'UZS' : c === 'USD' ? 'USD' : 'Наличные'}
          </button>
        ))}
      </div>

      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-hint)', marginBottom: 10 }}>
          Категория
        </div>
        {categories.isPending && <EmptyState title={t.common.loading} />}
        {categories.data && (
          <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 4 }}>
            {categories.data.map((cat) => (
              <button
                key={cat.id}
                type="button"
                onClick={() => setCategoryId(cat.id === categoryId ? null : cat.id)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 6,
                  width: 64,
                  flexShrink: 0,
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: 16,
                    background: cat.id === categoryId ? 'var(--color-link)' : 'var(--color-bg-secondary)',
                    color: cat.id === categoryId ? '#fff' : 'inherit',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 22,
                  }}
                >
                  {cat.icon ?? '📁'}
                </div>
                <div style={{ fontSize: 11, textAlign: 'center' }}>{cat.name}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      <input
        type="text"
        placeholder="Заметка (необязательно)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        style={{
          background: 'var(--color-bg)',
          border: 'none',
          borderRadius: 12,
          padding: '12px 14px',
          fontSize: 15,
          color: 'var(--color-text)',
          outline: 'none',
        }}
      />

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && submit.mutate()}>
        {submit.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      {submit.isError && (
        <ErrorState message="Не удалось сохранить операцию" onRetry={() => submit.mutate()} />
      )}
      {!canSubmit && amount.length > 0 && parsedAmount <= 0 && (
        <div style={{ color: 'var(--color-destructive)', fontSize: 13, textAlign: 'center' }}>
          Сумма должна быть больше нуля
        </div>
      )}
    </SubScreen>
  );
}
