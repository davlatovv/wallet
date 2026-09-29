import { SubScreen } from '../../shared/ui';

const TYPES = [
  { icon: '💳', title: 'Кредит', desc: 'Аннуитетный или дифференцированный, с графиком платежей' },
  { icon: '📆', title: 'Рассрочка', desc: 'Фиксированный ежемесячный платёж на N месяцев' },
  { icon: '📚', title: 'Учёба', desc: 'Контракт за обучение, оплата по семестрам' },
  { icon: '🔄', title: 'Постоянный расход', desc: 'Аренда, подписки — без даты окончания' },
];

/**
 * The four creation forms (docs/MINIAPP_PLAN.md task 3.12) aren't built yet —
 * this only shows the type choice from the wireframe so the reminders flow
 * is navigable end to end. Existing reminders can already be viewed and
 * paid via ReminderDetailPage, which is fully wired to the API.
 */
export function ReminderTypePickerPage() {
  return (
    <SubScreen title="Тип напоминания">
      <div style={{ fontSize: 13, color: 'var(--color-hint)' }}>
        Формы создания ещё не реализованы (задача 3.12 плана миграции).
      </div>
      {TYPES.map((type) => (
        <div
          key={type.title}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            background: 'var(--color-bg)',
            borderRadius: 'var(--radius-card)',
            padding: 16,
            opacity: 0.6,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 12,
              background: 'var(--color-bg-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 18,
              flexShrink: 0,
            }}
          >
            {type.icon}
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>{type.title}</div>
            <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>{type.desc}</div>
          </div>
        </div>
      ))}
    </SubScreen>
  );
}
