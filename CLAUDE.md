# CLAUDE.md — Engineering Contract: Wallet Telegram Bot

## 1. Project Overview

**System:** Telegram-бот для личных финансов  
**Stack:** Python 3.11+, aiogram 3, PostgreSQL, SQLAlchemy (async), Alembic, Docker  
**Architecture:** Clean Architecture (Domain → Application → Infrastructure → Presentation)

### Key Capabilities
- Учёт доходов и расходов с категориями
- Баланс и финансовая аналитика (день / неделя / месяц)
- Бюджеты с лимитами и уведомлениями
- Долги (я должен / мне должны)
- Копилка (savings goals)
- Рассрочки и кредиты
- Экспорт данных (CSV / Excel)
- Напоминания и уведомления

---

## 2. Architecture Principles

### Clean Architecture (строго соблюдается)
```
Domain → Application → Infrastructure → Presentation
  ↑            ↑              ↑               ↑
 Entities    UseCases      Repositories    Handlers
 (no deps)  (no framework) (SQLAlchemy)   (aiogram)
```

### Separation of Concerns
- **Domain:** только бизнес-логика, никаких импортов фреймворков
- **Application:** оркестрация, только через интерфейсы репозиториев
- **Infrastructure:** реализация репозиториев, ORM-модели, внешние сервисы
- **Presentation:** Telegram handlers, FSM, keyboards — только вызовы Use Cases

### Dependency Inversion
- Handlers зависят от Use Cases (не от репозиториев напрямую)
- Use Cases зависят от абстрактных интерфейсов репозиториев
- SQLAlchemy-репозитории реализуют эти интерфейсы

---

## 3. Coding Standards

### Async-First
```python
# ПРАВИЛЬНО
async def get_balance(user_id: int) -> Decimal: ...

# НЕПРАВИЛЬНО
def get_balance(user_id: int) -> Decimal: ...  # sync в async-контексте
```

### Naming Conventions
| Уровень        | Нейминг                              |
|----------------|--------------------------------------|
| Entity         | `Transaction`, `Budget`, `Debt`      |
| Use Case       | `AddExpenseUseCase`, `GetBalanceUseCase` |
| Repository IF  | `AbstractTransactionRepository`      |
| Repository IMPL| `SQLAlchemyTransactionRepository`    |
| Handler        | `expense_router`, `handle_add_expense` |
| FSM State      | `ExpenseStates`, `DebtStates`        |

### Type Annotations
- Обязательны везде: параметры, возвращаемые значения, поля классов
- `Decimal` для всех денежных значений (не `float`)
- `datetime` с timezone (UTC)

### Code Readability
- Максимум 1 публичный метод на Use Case класс
- Функции до 30 строк
- Нет магических чисел — только именованные константы

---

## 4. Folder Structure (фиксированная, не менять)

```
/app
  /domain
    /entities          # Dataclass-сущности без зависимостей
    /repositories      # Abstract интерфейсы репозиториев
    /exceptions        # Domain-исключения
    /value_objects     # ValueObjects (Money, Period и т.д.)
  /application
    /use_cases
      /transactions    # AddExpense, AddIncome, GetBalance
      /categories      # CreateCategory, ListCategories
      /budgets         # SetBudget, CheckBudgetLimit
      /debts           # AddDebt, SettleDebt
      /savings         # CreateSavingsGoal, AddToSavings
      /installments    # AddInstallment, PayInstallment
      /analytics       # GetDailyReport, GetMonthlyReport
      /export          # ExportCSV, ExportExcel
    /dto               # Input/Output DTOs (Pydantic)
    /interfaces        # Notification, Export интерфейсы
  /infrastructure
    /db
      /models          # SQLAlchemy ORM модели
      /repositories    # Реализации репозиториев
      /session         # Async session factory
    /notifications     # APScheduler реализация
    /export            # CSV/Excel генераторы
  /presentation
    /telegram
      /handlers        # aiogram routers
      /keyboards       # Inline/Reply keyboards
      /states          # FSM States
      /middlewares     # Auth, logging middleware
      /filters         # Custom filters
  /config
    settings.py        # Pydantic Settings
  /db
    /migrations        # Alembic migrations

main.py                # Точка входа
Dockerfile
docker-compose.yml
.env.example
alembic.ini
pyproject.toml
```

---

## 5. Rules (НАРУШЕНИЕ = БЛОКЕР)

### Запрещено
- ❌ SQL/ORM-запросы в handlers
- ❌ Бизнес-логика в handlers (handlers только вызывают Use Cases)
- ❌ Импорт SQLAlchemy в domain или application
- ❌ Импорт aiogram в domain или application
- ❌ `float` для денег (использовать `Decimal`)
- ❌ Прямые вызовы репозиториев из handlers (только через Use Cases)
- ❌ Дублирование логики между Use Cases
- ❌ Хардкод Telegram Bot Token или DB URL в коде

### Обязательно
- ✅ Все Use Cases получают зависимости через DI (конструктор)
- ✅ Все репозитории — только через абстрактные интерфейсы
- ✅ Все ошибки обрабатываются на уровне presentation
- ✅ Логирование на уровне application и infrastructure
- ✅ Валидация входных данных через DTO (Pydantic)
- ✅ Транзакционность через Unit of Work

---

## 6. Data Models

### Ключевые таблицы
```sql
users(id BIGINT PK, created_at, timezone)
transactions(id, user_id FK, amount NUMERIC(15,2), type ENUM, category_id FK, note, created_at)
categories(id, user_id FK, name, parent_id FK SELF-REF, icon, is_system)
budgets(id, user_id FK, category_id FK, limit_amount NUMERIC(15,2), period ENUM, start_date)
debts(id, user_id FK, counterparty, amount, type ENUM, due_date, status ENUM, description)
savings(id, user_id FK, name, target_amount, current_amount, deadline, status)
installments(id, user_id FK, name, total_amount, monthly_payment, months_total, months_paid, next_payment_date)
audit_logs(id, user_id FK, entity, entity_id, action, old_value JSONB, new_value JSONB, changed_at)
```

---

## 7. Development Workflow

### Строгий порядок разработки
```
1. Domain (entities, interfaces, exceptions)
      ↓
2. Application (use cases, DTOs)
      ↓
3. Infrastructure (ORM models, repositories, DB session)
      ↓
4. Presentation (handlers, FSM, keyboards)
```

### Перед каждым коммитом
- [ ] Нет нарушений архитектуры (см. Rules)
- [ ] Новые Use Cases покрыты логикой
- [ ] Нет hardcoded credentials
- [ ] Типизация соблюдена

---

## 8. FSM Conventions

```python
class ExpenseStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()
    waiting_for_note = State()
    confirming = State()
```

- Состояния именуются: `waiting_for_*`, `confirming`, `editing_*`
- Каждый flow в отдельном файле handler
- Данные FSM хранятся в `state.update_data()` — не в глобальных переменных

---

## 9. Telegram UX Constraints

- Только кнопки (inline keyboard) — никакого свободного текста кроме сумм/имён
- Максимум 3 шага до завершения действия (исключения: категории, долги)
- Callback data формат: `action:entity:id` (например, `select:category:42`)
- Все сообщения с разметкой `ParseMode.HTML`

---

## 10. Definition of Done

### Глобальный DoD (проект завершён когда):
- [ ] Пользователь может добавить доход и расход через бота
- [ ] Баланс корректно считается: `balance = sum(income) - sum(expense)`
- [ ] Категории создаются и поддерживают иерархию
- [ ] Бюджеты уведомляют при 80% и 100% использования
- [ ] Долги: создание, просмотр, закрытие (оба типа)
- [ ] Копилка: создание цели, пополнение, прогресс
- [ ] Рассрочки: добавление, фиксация платежа, остаток
- [ ] Отчёты: день, неделя, месяц с breakdown по категориям
- [ ] Экспорт в CSV и Excel работает
- [ ] Бот запускается через `docker-compose up`
- [ ] Миграции применяются автоматически при старте

### Per-Feature DoD
**Transactions:** создание, список, удаление, фильтрация по периоду  
**Categories:** CRUD, иерархия (parent/child), системные категории по умолчанию  
**Budgets:** создание, проверка лимита, уведомление  
**Debts:** CRUD, статус (active/settled/overdue), оба направления  
**Savings:** CRUD, пополнение, достижение цели  
**Installments:** CRUD, оплата месяца, расчёт остатка  
**Analytics:** агрегация за период, топ-5 категорий, динамика  
**Export:** CSV и XLSX файлы отдаются через бота

---

## 11. Environment Variables

```env
# Bot
BOT_TOKEN=

# Database
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_DB=
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://...

# App
DEBUG=false
LOG_LEVEL=INFO
TIMEZONE=UTC
```

---

## 12. Execution Plan Status

| Этап | Описание                        | Статус  |
|------|---------------------------------|---------|
| 0    | Scaffold, Docker, Config        | ⏳      |
| 1    | ORM Models & Migrations         | ⏳      |
| 2    | Domain Layer                    | ⏳      |
| 3    | Repository Layer                | ⏳      |
| 4    | Application (Use Cases)         | ⏳      |
| 5    | Telegram Handlers & FSM         | ⏳      |
| 6    | Analytics & Export              | ⏳      |
| 7    | Notifications                   | ⏳      |
| 8    | Quality & DevOps                | ⏳      |
