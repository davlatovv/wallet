import { createBrowserRouter } from 'react-router-dom';
import { HomePage } from '../pages/Home/HomePage';
import { TransactionsPage } from '../pages/Transactions/TransactionsPage';
import { TransactionDetailPage } from '../pages/Transactions/TransactionDetailPage';
import { AnalyticsPage } from '../pages/Analytics/AnalyticsPage';
import { MorePage } from '../pages/More/MorePage';
import { AddTransactionPage } from '../pages/AddTransaction/AddTransactionPage';
import { CategoriesPage } from '../pages/Categories/CategoriesPage';
import { CreateCategoryPage } from '../pages/Categories/CreateCategoryPage';
import { CategoryDetailPage } from '../pages/Categories/CategoryDetailPage';
import { BudgetsPage } from '../pages/Budgets/BudgetsPage';
import { BudgetFormPage } from '../pages/Budgets/BudgetFormPage';
import { DebtsPage } from '../pages/Debts/DebtsPage';
import { CreateDebtPage } from '../pages/Debts/CreateDebtPage';
import { DebtDetailPage } from '../pages/Debts/DebtDetailPage';
import { SavingsPage } from '../pages/Savings/SavingsPage';
import { CreateSavingsGoalPage } from '../pages/Savings/CreateSavingsGoalPage';
import { DepositPage } from '../pages/Savings/DepositPage';
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
  { path: '/transactions/:transactionId', element: <TransactionDetailPage /> },
  { path: '/analytics', element: <AnalyticsPage /> },
  { path: '/more', element: <MorePage /> },
  { path: '/add-transaction', element: <AddTransactionPage /> },
  { path: '/categories', element: <CategoriesPage /> },
  { path: '/categories/new', element: <CreateCategoryPage /> },
  { path: '/categories/:categoryId', element: <CategoryDetailPage /> },
  { path: '/budgets', element: <BudgetsPage /> },
  { path: '/budgets/new', element: <BudgetFormPage /> },
  { path: '/debts', element: <DebtsPage /> },
  { path: '/debts/new', element: <CreateDebtPage /> },
  { path: '/debts/:debtId', element: <DebtDetailPage /> },
  { path: '/savings', element: <SavingsPage /> },
  { path: '/savings/new', element: <CreateSavingsGoalPage /> },
  { path: '/savings/:goalId/deposit', element: <DepositPage /> },
  { path: '/reminders', element: <RemindersListPage /> },
  { path: '/reminders/new', element: <ReminderTypePickerPage /> },
  { path: '/reminders/new/credit', element: <CreateCreditReminderPage /> },
  { path: '/reminders/new/installment', element: <CreateInstallmentReminderPage /> },
  { path: '/reminders/new/education', element: <CreateEducationReminderPage /> },
  { path: '/reminders/new/regular', element: <CreateRegularReminderPage /> },
  { path: '/reminders/:reminderId', element: <ReminderDetailPage /> },
  { path: '/export', element: <ExportPage /> },
]);
