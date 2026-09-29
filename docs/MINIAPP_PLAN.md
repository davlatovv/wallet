# Wallet → Telegram Mini App: Migration Plan

Status: **Phase 2 (backend API) shipped — [PR #2](https://github.com/davlatovv/wallet/pull/2)**; Phase 1 wireframes [drafted](https://claude.ai/artifact/CKyns45Q1pqGuRXN7qeQpY), awaiting approval; **Phase 3 frontend started** on `feat/miniapp-web` (branched from the API branch) — ten screens wired to the real backend, verified in-browser end to end; reminder-creation forms (3.12), edit/delete UI, and tests (3.15) still open · Owner: davlatovv · Date: 2026-09-20

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

Conventions: money is serialized as a **decimal string with exactly 2 decimals** (never float), timestamps are ISO-8601 UTC, and errors use `{code, message, details}` (`NotFoundError`→404, validation→422, domain rule→409/400). OpenAPI is auto-generated and used to generate TS types for the frontend (`openapi-typescript`).

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
- ✅ **0.2** Create `tests/` with pytest, pytest-asyncio and pytest-mock config. Add tests for `Money`, `AddTransactionDTO`, `AddExpenseUseCase`, `AddIncomeUseCase` and `GetBalanceUseCase` (fake repos). DoD: `pytest` green in CI.
- ☐ **0.3** Add a `test` job to `.github/workflows/deploy.yml` (currently lint is only `py_compile`).
- ☐ **0.4** No domain yet (decided 2026-09-27): for local dev and review, run the `api`/`web` containers and expose them via a tunnel (ngrok or `cloudflared tunnel`), which gives an HTTPS URL Telegram will accept for a WebApp button — a Mini App requires HTTPS even in dev. Register that tunnel URL in BotFather (`/newapp` or `/mybots` → Bot Settings → Menu Button) so it can be opened from the bot for testing. Buying a domain and pointing DNS at the VPS moves to Phase 4 (4.3/4.4), right before the real deployment. DoD: a tunnel URL opens the (currently empty) `web` container over HTTPS from inside Telegram.

### Phase 1. Design and contract (no production code)
- ✅ **1.1** Reviewed; open questions resolved 2026-09-27 (see section 8).
- ✅ **1.2** Wireframes for all screens plus a navigation map (see 3.5). [Draft published](https://claude.ai/artifact/CKyns45Q1pqGuRXN7qeQpY) 2026-09-27 — Telegram-native light theme, phone-width (390×844) artboards: Home, Add-transaction sheet, Transactions, Analytics, More, Categories, Budgets, Debts, Savings, and the Reminders flow (type picker → credit detail with schedule and payment), plus a navigation-map artboard showing how they connect. Awaiting approval; not yet reviewed on a real device.
- ☐ **1.3** Design tokens (decided 2026-09-27: Telegram-native, no separate brand/Figma source). Map CSS variables directly to `Telegram.WebApp.themeParams` (`bg_color`, `text_color`, `hint_color`, `link_color`, `button_color`, `button_text_color`, `secondary_bg_color`, `destructive_text_color`), with a light/dark fallback for the rare case a client reports no theme. Spacing/typography follow Telegram's own iOS/Android type scale rather than a custom system. Component list: Button, Card, Sheet, Input, MoneyInput, CategoryChip, ProgressBar, ListItem, EmptyState.
- ☐ **1.4** Write the OpenAPI contract draft (schemas for money, pagination, errors) and review it against the screens. Every screen must map to endpoints.

### Phase 2. Backend: API layer
- ✅ **2.1** Add deps (`fastapi`, `uvicorn`, `pyjwt`, `python-multipart`) to `pyproject.toml`. Create the `presentation/api` skeleton, app factory, `/health`, error handlers, and CORS limited to the app origin.
- ✅ **2.2** `get_session` dependency (one transaction per request, mirroring `DbSessionMiddleware`) and `get_container`.
- ✅ **2.3** Telegram `initData` validation plus `POST /auth/telegram` and the JWT dependency `get_current_user`. Unit tests: valid, tampered, expired and missing hash.
- ✅ **2.4** Settings additions: `jwt_secret`, `jwt_ttl_minutes`, `webapp_url`, `cors_origins`, `api_port`.
- ✅ **2.5** `GET /me`, `PATCH /me` (timezone, validated against `pytz.all_timezones_set`), `GET /balance`, `GET /currency/usd-rate`; USD conversion lives in `PrepareTransactionUseCase`. _Bot handlers still convert USD and check budgets themselves rather than calling the shared use cases — left for Phase 5 cutover, tracked below._
- ✅ **2.6** New use cases + repo methods: `ListTransactions` (filters, cursor), `UpdateTransaction`, `DeleteTransaction`. Both must **reverse or reapply the user's account balances** consistently (see 0006 logic), in a single DB transaction. Tests for balance correctness. _Decisions: SAVINGS transactions are read-only here (managed via savings goals); type cannot change; a new category must belong to the user; rows are locked `FOR UPDATE`. Follow-up: `add_expense`/`add_income` do not yet check category ownership._
- ✅ **2.7** Transactions router (list, expense, income, patch, delete). The expense response includes `BudgetAlert`s.
- ✅ **2.8** Categories router. _System-category protection and parent/type validation moved from the bot UI into the use cases._
- ✅ **2.9** Budgets router. _`PUT /budgets` upserts per (category, period); `GET` returns spent/ratio. Fixed: category budgets were checked against ALL expenses._
- ✅ **2.10** Analytics router (`report`, `months`).
- ✅ **2.11** Debts router. _Added input validation and `DELETE /debts/{id}` (debts have no balance effect)._ Fill in gaps (settle validation, and check whether an edit or delete use case is needed).
- ✅ **2.12** Savings router. _Deposits only to ACTIVE goals; `add_funds` is now an atomic increment. No savings delete endpoint yet (needs a decision on returning funds)._
- ✅ **2.13** Reminders router (four create endpoints, detail, payment, delete). Reuse the DTOs and `CreditCalculator`. Add a schedule preview endpoint `POST /reminders/credit/preview`. _Done. Requests take only `first_payment_date` (payment day is derived). Fixed on the way: differential credits recorded/showed the first month's amount forever; payment dates drifted after short months (31st -> 28th); credits with interest were marked completed as soon as paid >= principal (e.g. after payment 8 of 12); double-tap could record a payment twice (now row-locked); bot accepted rates > 100% and terms > 600 months (now re-prompts)._
- ✅ **2.14** Export use case (`app/application/use_cases/export`) wrapping the exporters. Remove the `container._tx_repo` access. Router streams CSV/XLSX. _Done: `ExportTransactionsUseCase` wraps both exporters for any month; bot handler switched to it too._
- ✅ **2.15** Router-level tests (httpx `AsyncClient` + test DB or overridden container): auth required, cross-user isolation, error mapping. _Done for every router 2.5–2.14, plus uniform `{code,message,details}` error bodies; verified end-to-end on real Postgres._
- ✅ **2.16** Rate limiting (per user) and request logging (structlog, already a dependency). _Done: in-process sliding-window limiter (`rate_limit_requests`/`rate_limit_window_seconds`, default 60/60s), keyed by user id from the token, falling back to client IP for unauthenticated requests (so `/auth/telegram` and bad tokens cannot dodge it). `/health` is exempt. Every request is logged via structlog with method, path, status, duration and user id, including 429s. Single-process only — a multi-instance deployment needs a shared store (Redis) instead._

### Phase 3. Frontend
- ✅ **3.1** Scaffold `webapp/` (Vite, React, TS, router, TanStack Query), Telegram SDK init, theme mapping. _Done, with two substitutions: `oxlint` instead of ESLint/Prettier (this Vite version's own default; equivalent purpose), and no Vitest yet (bundled into 3.15, still open). i18n scaffold (`shared/i18n`) is structured for multiple locales, filled with Russian only._
- ✅ **3.2** Generated API client from OpenAPI (`openapi-fetch` + `openapi-typescript`, `npm run generate:api`) plus an auth layer (login from Telegram `initData`, in-memory token, retry-once-on-401). _Local dev mock done (`shared/telegram/init.ts`), including a real `mockTelegramEnv` — three genuine SDK bugs were hit and fixed getting it to actually render (see the frontend commit message: missing `signature` field, deprecated async mount methods, missing `TelegramWebviewProxy` transport). No silent token refresh yet — an expired token just re-logs in from `initData` on the next request, which needs no separate refresh flow since Telegram re-supplies fresh `initData` on every open anyway._
- ✅ **3.3** Shared UI kit (`shared/ui`: Card, Header, ListItem, TabBar, ProgressBar, StatTile, PrimaryButton, EmptyState, ErrorState, SubScreen) and the tab-bar app shell.
- ✅ **3.4** Home screen. Real balance, this-month totals, recent transactions, quick-add buttons.
- ◐ **3.5** Add-transaction form (expense and income, currency UZS/USD/CASH, real category chips) — done as a full page rather than a bottom sheet (simpler with React Router; revisit if the sheet feel matters). No live USD→UZS preview shown while typing (the server converts on submit; showing the estimate client-side is a small follow-up).
- ◐ **3.6** Transactions list — done (real data, newest first); filters/edit/delete UI not built yet (the API supports them, per 2.6/2.7).
- ✅ **3.7** Analytics. Period switch, totals, category breakdown bars.
- ◐ **3.8** Categories — list view (expense/income toggle) done; add/rename/delete UI not built.
- ◐ **3.9** Budgets — progress view done; create/edit UI not built.
- ◐ **3.10** Debts — list (grouped by direction) done; add/settle UI not built.
- ◐ **3.11** Savings — progress view done; create/deposit UI not built.
- ☐ **3.12** Reminders: list and detail (schedule, record-payment mutation) are done and real. The four **creation forms** are not built — `ReminderTypePickerPage` shows the type choice from the wireframe and says so explicitly rather than pretending to work.
- ◐ **3.13** Export and Settings — export (CSV/XLSX, real download via blob since the endpoint needs an auth header `Telegram.WebApp.downloadFile` can't attach) is done; a timezone/settings UI (backed by `PATCH /me` from 2.5) is not built.
- ☐ **3.14** Polish: empty and error states exist throughout; skeletons, haptics, safe-area insets, an accessibility pass and the bundle-size check are still open. _Early read: the production build is 136 KB gzip already, well under the 250 KB target, with none of the above yet._
- ☐ **3.15** Frontend tests (Vitest + MSW) — not started.

### Phase 4. Bot changes and deployment
- ☐ **4.1** `/start` sends a WebApp button (`web_app=WebAppInfo(url=...)`). Set the chat menu button via `set_chat_menu_button`.
- ☐ **4.2** Reminder notifications get an inline "Open" WebApp button that deep-links to the reminder (`startapp` param).
- ☐ **4.3** Docker: `api` service, `web` (nginx serving the Vite build, multi-stage Dockerfile), `caddy` service with `deploy/Caddyfile` (`/api/*` → api, else → web). Bot container no longer runs migrations. Add healthchecks.
- ☐ **4.4** Update GitHub Actions deploy: build the web bundle, `docker compose up -d --build`. New secrets: `JWT_SECRET` etc. go in the VPS `.env` (already preserved by the workflow). Add a post-deploy smoke test against `/health`.
- ☐ **4.5** Staging (downgraded to optional 2026-09-27: no production users yet). Skippable for solo testing; revisit once anyone besides the owner depends on the bot — create a second bot token and run the whole stack there first before touching the real one.
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

### Open decisions (found during 2.x)
- ~~Report windows were UTC-only~~ **Resolved:** `GET /analytics/report` now computes "today"/"this week"/"this month"/"this year" in the user's saved timezone (`GetReportUseCase.execute(..., timezone=...)`, backed by `PATCH /me`); defaults to UTC until a user sets one. Verified end-to-end on real Postgres (a day boundary visibly shifts after `PATCH /me`).
- **Budget windows are still rolling** (last 1/7/30 days from *now*, in UTC), not calendar periods, and not timezone-aware. Lower priority than the report boundary since it affects only which side of a day-old transaction a budget counts, not a whole 5-hour bucket.
- **Naive datetimes** sent by clients are interpreted as UTC.
- **Savings goals** cannot be deleted or cancelled via the API yet (needs a rule for returning funds).
- ~~Category ownership was only checked on the API path~~ **Resolved:** `AddExpenseUseCase`/`AddIncomeUseCase` now take an optional `category_repo` and reject a foreign `category_id` with 404; `Container` always supplies it, so both the bot and the API get the check. (The parameter is optional only so existing tests/call sites that don't care about it don't have to pass one.)
- **Bot handlers still convert USD and evaluate budget alerts themselves** rather than calling `PrepareTransactionUseCase`/the shared budget use cases — the two paths can drift. Tracked for the Phase 5 cutover, when the bot's own transaction entry is being retired anyway.

- **Recording a reminder payment does not create an expense** (parity with the bot), so paying a credit in the app does not change the balance. Decide whether it should (optional `record_expense` flag?).
- **Existing data:** credit reminders that the old logic marked `completed` early stay completed. A one-off SQL fix could reopen credits where `months_paid < months_total`.
- **Existing reminders whose `payment_day` differs from their next date** will snap to `payment_day` at their next recorded payment.
- **No way yet to create a reminder for a loan already partly paid** (`months_paid` starts at 0), nor to edit or disable (`reminder_enabled`) a reminder.

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

## 8. Open questions — resolved 2026-09-27

1. **Domain:** none yet. Development and review use a tunnel (ngrok or Cloudflare Tunnel) pointed at the local `api`/`web` containers; a real domain is bought/pointed at the VPS only when Phase 4 (deployment) starts. Task 0.4 updated below.
2. **Design:** Telegram-native styling — map colors from `Telegram.WebApp.themeParams` (light/dark, accent, button colors) directly, no separate brand palette. Task 1.3 updated below.
3. **Languages:** Russian only for v1, matching the current bot's text exactly. Uzbek/English stay in the Phase 6 backlog.
4. **Production users:** none — this is just the owner testing. The staging-bot task (4.5) is downgraded from mandatory to optional; the Mini App can be built and tested directly against the existing bot token until real users are on it.
