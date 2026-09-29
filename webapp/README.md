# Wallet Mini App (frontend)

React + TypeScript + Vite frontend for the Telegram Mini App described in
[`../docs/MINIAPP_PLAN.md`](../docs/MINIAPP_PLAN.md). Talks to the FastAPI
backend in `../app/presentation/api`.

## Stack

- **Vite + React + TypeScript** — `npm run dev` / `npm run build`.
- **`@telegram-apps/sdk-react`** — Telegram theme, back button, launch
  params. See `src/shared/telegram/init.ts` for environment detection and
  the local-dev mock (see below).
- **TanStack Query** — server state, caching, retry-on-401.
- **React Router** — one route per screen, matching the wireframes'
  navigation map.
- **`openapi-fetch`** — typed API client generated from the backend's own
  OpenAPI schema (`src/shared/api/schema.d.ts`, regenerated with
  `npm run generate:api` — needs the backend running locally first).

## Running locally

```bash
cp .env.example .env   # points VITE_API_BASE_URL at the backend
npm install
npm run dev
```

You'll also need the backend running (see the repo root `CLAUDE.md`) with
`CORS_ORIGINS` covering wherever Vite serves from (`http://localhost:5173`
by default).

### Outside Telegram

`initTelegram()` mocks the Telegram environment when the page isn't opened
inside a real Telegram client, so the UI renders normally. Its `initData` is
deliberately **unsigned** — `POST /api/v1/auth/telegram` rejects it, same as
it would reject anyone else's forged data, so login (and everything that
needs it) fails with a visible "Не удалось загрузить данные" / retry state
rather than pretending to be authenticated. That's expected: real testing
needs the real Telegram client, opening a dev tunnel URL from a chat (see
`docs/MINIAPP_PLAN.md` task 0.4).

## Structure

```
src/
  app/       # providers, router, query client
  pages/     # one folder per screen
  shared/
    api/     # generated schema + typed client + auth
    i18n/    # Russian strings (v1; see docs/MINIAPP_PLAN.md §8)
    telegram/# SDK init, back-button hook
    theme/   # Telegram theme params -> CSS variables
    ui/      # shared components (Card, ListItem, TabBar, ...)
```

## Status

Scaffolded per `docs/MINIAPP_PLAN.md` tasks 3.1–3.2, plus working screens for
Home, Transactions, Analytics, More, Categories, Budgets, Debts, Savings,
Reminders list/detail, Export, and the add-transaction form. The four
reminder-creation forms (task 3.12) aren't built yet — see
`src/pages/Reminders/ReminderTypePickerPage.tsx`.
