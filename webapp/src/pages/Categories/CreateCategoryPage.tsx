import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../../shared/api/client';
import { t } from '../../shared/i18n';
import { ErrorState, FormField, PrimaryButton, SegmentedControl, SubScreen, TextField } from '../../shared/ui';

type CategoryType = 'expense' | 'income';

export function CreateCategoryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const initialType = searchParams.get('type') === 'income' ? 'income' : 'expense';

  const [name, setName] = useState('');
  const [icon, setIcon] = useState('');
  const [categoryType, setCategoryType] = useState<CategoryType>(initialType);

  const submit = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/categories', {
        body: { name, icon: icon || null, category_type: categoryType },
      });
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] });
      navigate(-1);
    },
  });

  const canSubmit = name.trim().length > 0;

  return (
    <SubScreen title="Новая категория">
      <FormField label="Название">
        <TextField value={name} onChange={setName} placeholder="Спорт" />
      </FormField>
      <FormField label="Иконка (эмодзи, необязательно)">
        <TextField value={icon} onChange={setIcon} placeholder="🏋️" />
      </FormField>
      <FormField label="Тип">
        <SegmentedControl
          value={categoryType}
          onChange={setCategoryType}
          options={[
            { value: 'expense', label: 'Расход' },
            { value: 'income', label: 'Доход' },
          ]}
        />
      </FormField>

      <div style={{ flex: 1 }} />
      <PrimaryButton onClick={() => canSubmit && submit.mutate()}>
        {submit.isPending ? t.common.loading : t.common.save}
      </PrimaryButton>
      {submit.isError && (
        <ErrorState message="Не удалось создать категорию" onRetry={() => submit.mutate()} />
      )}
    </SubScreen>
  );
}
