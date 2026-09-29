/**
 * Russian strings for v1 (see docs/MINIAPP_PLAN.md §8 — Russian only, matching
 * the bot). The nested shape is deliberate: adding uz.ts/en.ts later (backlog,
 * Phase 6) means copying this file's keys, not restructuring call sites.
 */
export const ru = {
  common: {
    save: 'Сохранить',
    cancel: 'Отмена',
    add: 'Добавить',
    delete: 'Удалить',
    edit: 'Изменить',
    loading: 'Загрузка…',
    retry: 'Повторить',
    errorGeneric: 'Что-то пошло не так',
    currencyUZS: 'UZS',
  },
  tabs: {
    home: 'Главная',
    transactions: 'Операции',
    analytics: 'Аналитика',
    more: 'Ещё',
  },
  home: {
    title: 'Wallet',
    totalBalance: 'Общий баланс',
    cash: 'Наличные',
    card: 'Карта',
    usd: 'USD',
    expense: 'Расход',
    income: 'Доход',
    thisMonth: 'Этот месяц',
    incomeLabel: 'Доходы',
    expenseLabel: 'Расходы',
    balanceLabel: 'Баланс',
    recentTransactions: 'Последние операции',
    viewAll: 'Все',
  },
  more: {
    title: 'Ещё',
    finance: 'Финансы',
    categories: 'Категории',
    budgets: 'Бюджеты',
    debts: 'Долги',
    savings: 'Копилка',
    reminders: 'Регулярные платежи',
    data: 'Данные',
    export: 'Экспорт и настройки',
  },
  errors: {
    loginFailed: 'Не удалось войти. Откройте приложение через Telegram.',
    loadFailed: 'Не удалось загрузить данные',
  },
} as const;

export type Messages = typeof ru;
