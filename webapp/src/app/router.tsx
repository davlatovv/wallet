import { createBrowserRouter } from 'react-router-dom';
import { HomePage } from '../pages/Home/HomePage';
import { TransactionsPage } from '../pages/Transactions/TransactionsPage';
import { AnalyticsPage } from '../pages/Analytics/AnalyticsPage';
import { MorePage } from '../pages/More/MorePage';
import { AddTransactionPage } from '../pages/AddTransaction/AddTransactionPage';
import { CategoriesPage } from '../pages/Categories/CategoriesPage';
import { BudgetsPage } from '../pages/Budgets/BudgetsPage';
import { DebtsPage } from '../pages/Debts/DebtsPage';
import { SavingsPage } from '../pages/Savings/SavingsPage';
import { RemindersListPage } from '../pages/Reminders/RemindersListPage';
import { ReminderTypePickerPage } from '../pages/Reminders/ReminderTypePickerPage';
import { ReminderDetailPage } from '../pages/Reminders/ReminderDetailPage';
import { CreateCreditReminderPage } from '../pages/Reminders/CreateCreditReminderPage';
import { CreateInstallmentReminderPage } from '../pages/Reminders/CreateInstallmentReminderPage';
import { CreateEducationReminderPage } from '../pages/Reminders/CreateEducationReminderPage';
import { CreateRegularReminderPage } from '../pages/Reminders/CreateRegularReminderPage';
import { ExportPage } from '../pages/Export/ExportPage';

/**
 * Paths mirror the wireframe navigation map (docs/MINIAPP_PLAN.md §3.5 /
 * the published wireframes artifact) one screen per route. The four tab
 * routes render <TabBar/>; every other route is reached from one of them
 * or from "More" and shows Telegram's hardware back button instead
 * (see shared/telegram/useBackButton.ts).
 */
export const router = createBrowserRouter([
  { path: '/', element: <HomePage /> },
  { path: '/transactions', element: <TransactionsPage /> },
  { path: '/analytics', element: <AnalyticsPage /> },
  { path: '/more', element: <MorePage /> },
  { path: '/add-transaction', element: <AddTransactionPage /> },
  { path: '/categories', element: <CategoriesPage /> },
  { path: '/budgets', element: <BudgetsPage /> },
  { path: '/debts', element: <DebtsPage /> },
  { path: '/savings', element: <SavingsPage /> },
  { path: '/reminders', element: <RemindersListPage /> },
  { path: '/reminders/new', element: <ReminderTypePickerPage /> },
  { path: '/reminders/new/credit', element: <CreateCreditReminderPage /> },
  { path: '/reminders/new/installment', element: <CreateInstallmentReminderPage /> },
  { path: '/reminders/new/education', element: <CreateEducationReminderPage /> },
  { path: '/reminders/new/regular', element: <CreateRegularReminderPage /> },
  { path: '/reminders/:reminderId', element: <ReminderDetailPage /> },
  { path: '/export', element: <ExportPage /> },
]);
