# Wallet → Telegram Mini App: Migration Plan

Status: **draft for review** · Owner: davlatovv · Date: 2026-09-20

## 1. Goal and decisions

Move all user-facing logic from chat handlers (aiogram FSM flows) to a Telegram Mini App (web UI opened inside Telegram). The bot stays only as an entry point and notification channel.

| Decision | Choice |
|---|---|
| Frontend | React + TypeScript + Vite, TanStack Query, `@telegram-apps/sdk-react` |
| Backend | FastAPI in the **same repo**, new `presentation/api` layer, existing use cases and `Container` reused |
| Bot role | Thin launcher (`/start` → "Open app" WebApp button) + APScheduler reminders. FSM handlers removed at the end |
| Hosting | Existing VPS + Docker, Caddy reverse proxy with automatic HTTPS (a Mini App requires HTTPS) |
| Auth | Validate Telegram `initData` (HMAC with the bot token) → short-lived JWT |
| DB | PostgreSQL, same database. `users.id` stays the Telegram id, so **no data migration for existing users** |

Non-goals (v1): multi-user sharing/families, web login outside Telegram, native apps, full offline mode.

## 2. Current state (what we are migrating)

Handlers today (`app/presentation/telegram/handlers/`): `expense`, `income`, `analytics`, `categories`, `budgets`, `debts`, `savings`, `reminders`, `export`, `start`. About 2000 lines, mostly FSM dialogs and formatting.

Reusable as is:
- Domain entities, repository interfaces, SQLAlchemy models and repositories.
- Use cases: add expense/income, balance, report, categories CRUD, budgets, debts, savings, reminders (4 types + payments).
- `Container` (`app/infrastructure/container.py`): needs only a session. Today `DbSessionMiddleware` gives one transaction per update, and the API will do the same with one transaction per request.

Gaps found while reading the code (must be filled for the API):
1. No use cases to **list, edit or delete transactions**. There is only add and aggregate.
2. `app/application/use_cases/export` and `installments` are empty. Exporters are called directly from the handler with `container._tx_repo`, a private attribute.
3. Handlers contain presentation and business logic mixed together (USD rate lookup, currency to account mapping, debt selection).
4. No `tests/` directory at all.
5. Working tree has **uncommitted multi-currency and account-balance changes** (migration `0006`). They must be finished and committed before the API is built on top.

## 3. Target architecture

```
Telegram client
  ├── Bot chat ── /start ── [Open app] WebApp button ──┐
  └── Mini App (WebView) ◄─────────────────────────────┘
        React SPA  ──HTTPS──►  Caddy  ──►  /api/*  → FastAPI (api container)
                                     └──►  /*      → static SPA build (web container)
Bot process (aiogram, polling → later webhook) + APScheduler ─► sends reminders
FastAPI + Bot  ──►  Container / use cases  ──►  PostgreSQL
```

### 3.1 Repo layout (additions)

```
app/presentation/api/
  main.py              # FastAPI app factory, CORS, error handlers, lifespan
  deps.py              # get_session, get_container, get_current_user
  auth/telegram.py     # initData validation, JWT issue/verify
  schemas/             # pydantic request/response models (API contract)
  routers/             # transactions, balance, categories, budgets, debts,
                       # savings, reminders, analytics, export, me, currency
  errors.py            # domain exceptions → HTTP codes
app/presentation/telegram/   # shrinks to start.py + notification sending
webapp/                      # React app (Vite)
  src/{app,pages,features,entities,shared}/
deploy/Caddyfile
docker-compose.yml           # + api, web, caddy
```

Layer rule is unchanged: routers call use cases only. There is no SQL in routers, and no aiogram imports in the API.

### 3.2 Process model

- `api` container: `uvicorn app.presentation.api.main:app`. Runs migrations on start (move `run_migrations` out of `main.py` into a shared helper, run **only in api**, so two containers do not race).
- `bot` container: `python main.py` (polling, scheduler). No migrations.
- The scheduler stays in the bot process for v1. Reminder text gets a button to open the app on that reminder.

### 3.3 Auth flow

1. The Mini App reads `window.Telegram.WebApp.initData`.
2. `POST /api/v1/auth/telegram` with `{initData}`. The server verifies the HMAC using the bot token, checks that `auth_date` is under 1 hour old, and upserts the user via `EnsureUserExistsUseCase`. It returns `{access_token, expires_in}` (JWT, 1h; re-auth silently on 401 from fresh `initData`).
3. All other endpoints require `Authorization: Bearer`. `user_id` comes **only from the token**, never from the request body, so users cannot access each other's data.

### 3.4 API surface (v1, `/api/v1`)

| Area | Endpoints |
|---|---|
| Auth / profile | `POST /auth/telegram`, `GET /me` (balances by account, timezone), `PATCH /me` (timezone) |
| Balance | `GET /balance` (cash / card / currency / total) |
| Transactions | `GET /transactions` (filters: type, category, date range, cursor pagination), `POST /transactions/expense`, `POST /transactions/income`, `PATCH /transactions/{id}`, `DELETE /transactions/{id}` |
| Currency | `GET /currency/usd-rate` (CBU, cached) |
| Categories | `GET/POST /categories`, `PATCH/DELETE /categories/{id}` |
| Budgets | `GET /budgets`, `PUT /budgets` (upsert), `DELETE /budgets/{id}`. Budget alerts are returned inside the expense response |
| Analytics | `GET /analytics/report?period=day|week|month|year`, `GET /analytics/months` |
| Debts | `GET /debts?status=`, `POST /debts`, `POST /debts/{id}/settle` |
| Savings | `GET /savings`, `POST /savings`, `POST /savings/{id}/deposit` |
| Reminders | `GET /reminders`, `POST /reminders/{credit|installment|education|regular}`, `GET /reminders/{id}`, `POST /reminders/{id}/payments`, `DELETE /reminders/{id}` |
| Export | `GET /export/transactions?format=csv|xlsx&month=YYYY-MM` (file download) |

Conventions: money is serialized as a **decimal string** (never float), timestamps are ISO-8601 UTC, and errors use `{code, message, details}` (`NotFoundError`→404, validation→422, domain rule→409/400). OpenAPI is auto-generated and used to generate TS types for the frontend (`openapi-typescript`).

### 3.5 Frontend structure and UX

Navigation is a bottom tab bar: **Home · Transactions · Analytics · More**. "More" contains Budgets, Debts, Savings, Reminders, Categories, Export and Settings.

Screens (each replaces a bot flow):

| Screen | Replaces | Notes |
|---|---|---|
| Home | balance view | Balance card with the cash/card/USD split, this month's income vs expense, budget alerts, quick "+ Expense" / "+ Income" actions |
| Add transaction (bottom sheet) | `expense.py`, `income.py` FSM | One form: amount, currency (UZS/USD/CASH), category chips, note. Shows live UZS equivalent for USD. Uses Telegram `MainButton` for submit |
| Transactions | none (new) | Filterable list, edit and delete by swipe/long-press |
| Analytics | `analytics.py` | Period switch, category breakdown chart, income/expense totals |
| Categories | `categories.py` | List by type, add/rename/delete |
| Budgets | `budgets.py` | Progress bars, thresholds (80% warn / 100% critical) |
| Debts | `debts.py` | Owed to me / I owe, settle action |
| Savings | `savings.py` | Goal cards with progress, deposit |
| Reminders | `reminders.py` (631 lines) | Type picker → per-type form, credit schedule preview (annuity/differential), record payment, progress |
| Export | `export.py` | Pick month and format, then download (`Telegram.WebApp.downloadFile` or an `openLink` fallback) |

Cross-cutting: Telegram theme params mapped to CSS variables (light/dark automatic), `BackButton`, haptic feedback, safe-area insets, i18n scaffold (Russian first, matching the bot; Uzbek/English later), number formatting `1 234 567,00`, skeleton loaders and optimistic updates via TanStack Query.

**Design step:** before building, produce low-fidelity wireframes for the ten screens (Figma if you have a file, otherwise HTML mockups in this repo). Approve them before Phase 3.

## 4. Task plan

Legend: ☐ todo. Each task is small enough for one PR. "DoD" is the definition of done.

### Phase 0. Baseline and prerequisites
- ☐ **0.1** Finish and commit the in-progress multi-currency / account-balance work (`0006_add_user_account_balances.py`, transaction and user changes). Run `alembic upgrade head` on a scratch DB. DoD: clean `git status`.
- ☐ **0.2** Create `tests/` with pytest, pytest-asyncio and pytest-mock config. Add tests for `Money`, `AddTransactionDTO`, `AddExpenseUseCase`, `AddIncomeUseCase` and `GetBalanceUseCase` (fake repos). DoD: `pytest` green in CI.
- ☐ **0.3** Add a `test` job to `.github/workflows/deploy.yml` (currently lint is only `py_compile`).
- ☐ **0.4** Decide the domain name and point DNS at the VPS. Create a bot in BotFather, and later set the Mini App URL and menu button. DoD: `https://<domain>` reachable.

### Phase 1. Design and contract (no production code)
- ☐ **1.1** Review and approve this document (architecture, endpoint list).
- ☐ **1.2** Wireframes for all screens plus a navigation map (see 3.5). Approve.
- ☐ **1.3** Design tokens: colors mapped from Telegram theme params, spacing, typography, component list (Button, Card, Sheet, Input, MoneyInput, CategoryChip, ProgressBar, ListItem, EmptyState).
- ☐ **1.4** Write the OpenAPI contract draft (schemas for money, pagination, errors) and review it against the screens. Every screen must map to endpoints.

### Phase 2. Backend: API layer
- ☐ **2.1** Add deps (`fastapi`, `uvicorn`, `pyjwt`, `python-multipart`) to `pyproject.toml`. Create the `presentation/api` skeleton, app factory, `/health`, error handlers, and CORS limited to the app origin.
- ☐ **2.2** `get_session` dependency (one transaction per request, mirroring `DbSessionMiddleware`) and `get_container`.
- ☐ **2.3** Telegram `initData` validation plus `POST /auth/telegram` and the JWT dependency `get_current_user`. Unit tests: valid, tampered, expired and missing hash.
- ☐ **2.4** Settings additions: `jwt_secret`, `jwt_ttl_minutes`, `webapp_url`, `cors_origins`, `api_port`.
- ☐ **2.5** `GET /me`, `PATCH /me`, `GET /balance`, `GET /currency/usd-rate`. Move USD-rate and currency to account logic from handlers into use cases so the API and bot share it.
- ☐ **2.6** New use cases + repo methods: `ListTransactions` (filters, cursor), `UpdateTransaction`, `DeleteTransaction`. Both must **reverse or reapply the user's account balances** consistently (see 0006 logic), in a single DB transaction. Tests for balance correctness.
- ☐ **2.7** Transactions router (list, expense, income, patch, delete). The expense response includes `BudgetAlert`s.
- ☐ **2.8** Categories router.
- ☐ **2.9** Budgets router.
- ☐ **2.10** Analytics router (`report`, `months`).
- ☐ **2.11** Debts router. Fill in gaps (settle validation, and check whether an edit or delete use case is needed).
- ☐ **2.12** Savings router.
- ☐ **2.13** Reminders router (four create endpoints, detail, payment, delete). Reuse the DTOs and `CreditCalculator`. Add a schedule preview endpoint `POST /reminders/credit/preview`.
- ☐ **2.14** Export use case (`app/application/use_cases/export`) wrapping the exporters. Remove the `container._tx_repo` access. Router streams CSV/XLSX.
- ☐ **2.15** Router-level tests (httpx `AsyncClient` + test DB or overridden container): auth required, cross-user isolation, error mapping.
- ☐ **2.16** Rate limiting (per user) and request logging (structlog, already a dependency).

### Phase 3. Frontend
- ☐ **3.1** Scaffold `webapp/` (Vite, React, TS, ESLint, Prettier, Vitest), Telegram SDK init, theme mapping, router, TanStack Query, i18n scaffold.
- ☐ **3.2** Generated API client from OpenAPI plus an auth layer (login on start, silent refresh, 401 retry). Local dev mock: Telegram environment mock for a browser (`mockTelegramEnv`).
- ☐ **3.3** Shared UI kit (components from 1.3) and app shell with the tab bar.
- ☐ **3.4** Home screen.
- ☐ **3.5** Add-transaction sheet (expense and income, currency handling, category chips).
- ☐ **3.6** Transactions list (filters, edit, delete).
- ☐ **3.7** Analytics.
- ☐ **3.8** Categories.
- ☐ **3.9** Budgets.
- ☐ **3.10** Debts.
- ☐ **3.11** Savings.
- ☐ **3.12** Reminders (biggest: type picker, four forms, credit preview, payment).
- ☐ **3.13** Export and Settings.
- ☐ **3.14** Polish: empty and error states, skeletons, haptics, safe-area, accessibility pass, bundle-size check (target under 250 KB gzip initial).
- ☐ **3.15** Frontend tests: key flows (add expense, edit tx, create reminder) with MSW.

### Phase 4. Bot changes and deployment
- ☐ **4.1** `/start` sends a WebApp button (`web_app=WebAppInfo(url=...)`). Set the chat menu button via `set_chat_menu_button`.
- ☐ **4.2** Reminder notifications get an inline "Open" WebApp button that deep-links to the reminder (`startapp` param).
- ☐ **4.3** Docker: `api` service, `web` (nginx serving the Vite build, multi-stage Dockerfile), `caddy` service with `deploy/Caddyfile` (`/api/*` → api, else → web). Bot container no longer runs migrations. Add healthchecks.
- ☐ **4.4** Update GitHub Actions deploy: build the web bundle, `docker compose up -d --build`. New secrets: `JWT_SECRET` etc. go in the VPS `.env` (already preserved by the workflow). Add a post-deploy smoke test against `/health`.
- ☐ **4.5** Staging: create a second bot token and run the whole stack there first.
- ☐ **4.6** Update `CLAUDE.md` / `AGENTS.md` (structure, run commands, new layers) once merged.

### Phase 5. Cutover
- ☐ **5.1** Beta with the owner and a few users while the old bot flows still work (both hit the same DB and use cases).
- ☐ **5.2** Freeze the bot flows: the main menu is replaced by the "Open app" button. Old reply-keyboard buttons answer "use the app".
- ☐ **5.3** After one to two stable weeks, delete the FSM handlers, `states/`, unused keyboards and the `MemoryStorage` dispatcher config. Keep only `start.py` and notifications.
- ☐ **5.4** Retro: check the error rate, latency and any user feedback. Plan v2.

### Phase 6. Later (backlog)
Bot webhook mode instead of polling · scheduler moved to a separate worker or DB-backed jobstore · Uzbek/English i18n · recurring transactions · receipts / photo attach · charts over time · PWA/offline queue · shared budgets.

## 5. Data and migration notes

- **No user migration**: Telegram ids are primary keys, so the same users and rows work in the Mini App.
- Possible schema additions (each via Alembic `NNNN_*.py`, reviewed by hand):
  - `transactions`: index on `(user_id, created_at DESC)` for pagination; optional `updated_at`.
  - `users`: `language`, `last_seen_at`.
  - Optional `audit_log` writes for edit/delete (the model already exists).
- Money stays `Numeric(15,2)` UZS. The API never uses floats.
- Editing or deleting a transaction must adjust `users.*_balance` atomically. Add a reconciliation script (recompute balances from transactions) as a safety net.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Balance drift on edit/delete | Same-transaction updates, tests (2.6), reconcile script |
| `initData` replay / theft | 1h `auth_date` window, short JWT, HTTPS only, user id only from token |
| Two containers running migrations | Only `api` migrates |
| Telegram WebView quirks (iOS keyboard, safe areas, file downloads) | Test on iOS and Android early (3.2) and use the SDK helpers |
| Scope creep in Reminders screen | Ship the four forms behind one shared form component, and preview only for credit |
| No existing tests | Phase 0.2 before touching logic, use-case tests before refactors |

## 7. Suggested order and rough sizing

Phase 0 (1–2 d) → Phase 1 (2–3 d) → Phase 2 (5–7 d) ‖ Phase 3 (7–10 d, starts after 2.5 with mocks) → Phase 4 (2 d) → Phase 5 (1–2 wk soak). The critical path is the contract (1.4) → the generated client (3.2).

## 8. Open questions

1. Domain name for the Mini App (needed for 0.4 and BotFather)?
2. Do you have a Figma file / brand preferences, or should the wireframes follow Telegram-native styling?
3. Languages for v1: Russian only, or Russian + Uzbek?
4. Is the current bot data used by other people today (production users), which would make the staging bot (4.5) mandatory?
