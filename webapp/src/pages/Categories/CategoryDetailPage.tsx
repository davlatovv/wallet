import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { confirmDialog } from '../../shared/telegram/confirmDialog';
import type { components } from '../../shared/api/schema';
import { EmptyState, ErrorState, FormField, PrimaryButton, SubScreen, TextField } from '../../shared/ui';

type Category = components['schemas']['CategoryResponse'];

/** No GET /categories/{id} on the backend — find it in the full list, same
 * approach as TransactionDetailPage. */
export function CategoryDetailPage() {
  const { categoryId } = useParams<{ categoryId: string }>();
  const id = Number(categoryId);

  const query = useQuery({
    queryKey: ['categories', 'all'],
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/categories');
      if (error) throw error;
      return data;
    },
  });
  const cat = query.data?.find((item) => item.id === id);

  if (query.isPending) {
    return (
      <SubScreen title="Категория">
        <EmptyState title={t.common.loading} />
      </SubScreen>
    );
  }
  if (query.isError) {
    return (
      <SubScreen title="Категория">
        <ErrorState message={t.errors.loadFailed} onRetry={() => query.refetch()} />
      </SubScreen>
    );
  }
  if (!cat) {
    return (
      <SubScreen title="Категория">
        <EmptyState title="Категория не найдена" />
      </SubScreen>
    );
  }

  // Keyed by id: see TransactionDetailPage for why (avoids an effect to
  // sync local state in after the async fetch resolves).
  return <CategoryEditForm key={cat.id} cat={cat} />;
}

function CategoryEditForm({ cat }: { cat: Category }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState(cat.name);
  const [icon, setIcon] = useState(cat.icon ?? '');

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['categories'] });

  const save = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.PATCH('/api/v1/categories/{category_id}', {
        params: { path: { category_id: cat.id } },
        body: { name, icon: icon || null },
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
      const { error } = await apiClient.DELETE('/api/v1/categories/{category_id}', {
        params: { path: { category_id: cat.id } },
      });
      if (error) throw error;
    },
    onSuccess: () => {
      invalidate();
      navigate(-1);
    },
  });

  const canSubmit = name.trim().length > 0;

  return (
    <SubScreen title={cat.name}>
      <FormField label="Название">
        <TextField value={name} onChange={setName} />
      </FormField>
      <FormField label="Иконка (эмодзи, необязательно)">
        <TextField value={icon} onChange={setIcon} />
      </FormField>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && save.mutate()}>
        {save.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      <PrimaryButton
        variant="danger"
        onClick={() => confirmDialog('Удалить категорию?').then((ok) => ok && remove.mutate())}
      >
        {remove.isPending ? t.common.loading : t.common.delete}
      </PrimaryButton>
      {save.isError && (
        <ErrorState message="Не удалось сохранить изменения" onRetry={() => save.mutate()} />
      )}
      {remove.isError && (
        <ErrorState message="Не удалось удалить категорию" onRetry={() => remove.mutate()} />
      )}
    </SubScreen>
  );
}
