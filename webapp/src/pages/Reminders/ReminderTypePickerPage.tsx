import { SubScreen } from '../../shared/ui';
import { NavLink } from 'react-router-dom';

const TYPES = [
  {
    icon: '💳',
    title: 'Кредит',
    desc: 'Аннуитетный или дифференцированный, с графиком платежей',
    to: '/reminders/new/credit',
  },
  {
    icon: '📆',
    title: 'Рассрочка',
    desc: 'Фиксированный ежемесячный платёж на N месяцев',
    to: '/reminders/new/installment',
  },
  {
    icon: '📚',
    title: 'Учёба',
    desc: 'Контракт за обучение, оплата по семестрам',
    to: '/reminders/new/education',
  },
  {
    icon: '🔄',
    title: 'Постоянный расход',
    desc: 'Аренда, подписки — без даты окончания',
    to: '/reminders/new/regular',
  },
];

export function ReminderTypePickerPage() {
  return (
    <SubScreen title="Тип напоминания">
      {TYPES.map((type) => (
        <NavLink
          key={type.title}
          to={type.to}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            background: 'var(--color-bg)',
            borderRadius: 'var(--radius-card)',
            padding: 16,
            color: 'var(--color-text)',
            textDecoration: 'none',
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
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 600 }}>{type.title}</div>
            <div style={{ fontSize: 12, color: 'var(--color-hint)' }}>{type.desc}</div>
          </div>
          <div style={{ color: 'var(--color-hint)', fontSize: 18 }}>›</div>
        </NavLink>
      ))}
    </SubScreen>
  );
}
