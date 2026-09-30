import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import {
  Card,
  EmptyState,
  ErrorState,
  IconAvatar,
  ListItem,
  PrimaryButton,
  SubScreen,
} from '../../shared/ui';

type CategoryType = 'expense' | 'income';

export function CategoriesPage() {
  const [type, setType] = useState<CategoryType>('expense');

  const query = useQuery({
    queryKey: ['categories', type],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/categories', {
        params: { query: { type } },
      });
      if (error) throw error;
      return data;
    },
  });

  return (
    <SubScreen title={t.more.categories}>
      <div style={{ display: 'flex', background: 'var(--color-bg-secondary)', borderRadius: 12, padding: 3 }}>
        {(['expense', 'income'] as const).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setType(v)}
            style={{
              flex: 1,
              textAlign: 'center',
              padding: '9px 0',
              borderRadius: 9,
              fontSize: 13,
              border: 'none',
              cursor: 'pointer',
              fontWeight: type === v ? 600 : 400,
              background: type === v ? 'var(--color-link)' : 'transparent',
              color: type === v ? 'var(--color-button-text)' : 'var(--color-text)',
            }}
          >
            {v === 'expense' ? 'Расходы' : 'Доходы'}
          </button>
        ))}
      </div>

      {query.isPending && <EmptyState title={t.common.loading} />}
      {query.isError && <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />}
      {query.data && query.data.length === 0 && <EmptyState title="Нет категорий" />}
      {query.data && query.data.length > 0 && (
        <Card padding="4px 12px">
          {query.data.map((cat, i) => (
            <ListItem
              key={cat.id}
              href={cat.is_system ? undefined : `/categories/${cat.id}`}
              border={i < query.data.length - 1}
              left={
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <IconAvatar>{cat.icon ?? '📁'}</IconAvatar>
                  <div style={{ fontSize: 15 }}>
                    {cat.name} {cat.is_system && <span style={{ fontSize: 12 }}>🔒</span>}
                  </div>
                </div>
              }
              right={
                cat.is_system ? null : <span style={{ color: 'var(--color-hint)', fontSize: 17 }}>›</span>
              }
            />
          ))}
        </Card>
      )}

      <PrimaryButton variant="outline" href={`/categories/new?type=${type}`}>
        + Добавить категорию
      </PrimaryButton>
    </SubScreen>
  );
}
