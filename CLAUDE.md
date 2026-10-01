# Wallet Bot — CLAUDE.md

Telegram Mini App для личных финансов. Python 3.10+, FastAPI, aiogram 3, PostgreSQL, SQLAlchemy async, Alembic, APScheduler, Docker; фронтенд — React + TypeScript + Vite (`webapp/`).

Вся функциональность для пользователя — в Mini App (`webapp/`), который обращается к FastAPI (`app/presentation/api`). Бот (`app/presentation/telegram`) — это только `/start` с кнопкой «Открыть приложение» и уведомления о платежах; диалоговых хендлеров с кнопками/FSM больше нет (см. `docs/MINIAPP_PLAN.md`, Phase 5 — миграция завершена).

## Запуск

```bash
docker-compose up --build      # PostgreSQL + бот (long-polling, уведомления)
python main.py                 # бот локально (нужен .env)
uvicorn app.presentation.api.main:app --reload --port 8000   # API локально
cd webapp && npm install && npm run dev                      # фронтенд (Vite, :5173)
```

`.env` обязателен для бота и API. Переменные:
- `BOT_TOKEN`, `DATABASE_URL` (asyncpg-формат) — обязательные.
- `JWT_SECRET` — обязателен для API (`create_app()` падает без него); чем подписываются выданные Mini App токены.
- `CORS_ORIGINS` — через запятую, источники фронтенда (например `http://localhost:5173`, домен или туннель Mini App).
- `WEBAPP_URL` — https-адрес Mini App; без него бот отправляет `/start` без кнопки.
- Опционально: `LOG_LEVEL`, `TIMEZONE`, `DEBUG`, `JWT_TTL_MINUTES`, `RATE_LIMIT_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS`.

Для фронтенда — `webapp/.env` (`VITE_API_BASE_URL`, см. `webapp/.env.example`).

Миграции применяются автоматически при старте бота через `alembic upgrade head` (subprocess в `main.py:run_migrations`). API миграции на себя не берёт — значит, перед первым запуском `uvicorn` либо запустите бота один раз, либо выполните `alembic upgrade head` вручную.

## Структура

```
main.py                                  # точка входа бота: polling + APScheduler
app/
  config/settings.py                     # pydantic-settings, читает .env (бот + API)
  domain/
    entities/                            # dataclass-сущности (без ORM)
    repositories/                        # абстрактные интерфейсы репозиториев
    value_objects/                       # Money, CreditCalculator
    exceptions/                          # базовые доменные исключения
  application/
    use_cases/                           # бизнес-логика, по одному модулю на группу
    dto/                                 # входные/выходные данные use cases
    interfaces/                          # абстракции внешних сервисов
  infrastructure/
    container.py                         # DI-контейнер (Container класс)
    db/
      models/                            # SQLAlchemy ORM-модели
      repositories/                      # реализации репозиториев
      session/factory.py                 # create_engine, async_session_factory
    currency/cbu_client.py               # курс USD с ЦБ Узбекистана
    export/                              # excel_exporter.py, csv_exporter.py
    notifications/scheduler.py           # APScheduler: уведомления о платежах
  presentation/
    api/                                 # FastAPI — вся функциональность Mini App
      main.py                            # app factory, CORS, error handlers
      deps.py                            # get_session, get_container, auth
      auth/                              # проверка Telegram initData, JWT
      routers/                           # по одному файлу на ресурс
      schemas/                           # pydantic request/response модели
    telegram/                            # бот: только /start и уведомления
      handlers/start.py
      keyboards/webapp.py                # кнопка «Открыть приложение»
      middlewares/
        db_session.py                    # открывает сессию + создаёт Container
        register_user.py                 # авто-регистрация пользователя
      router.py
webapp/                                  # Mini App: React + TypeScript + Vite
  src/{app,pages,shared}/                # см. webapp/README.md
db/
  migrations/versions/                   # Alembic-миграции
docs/MINIAPP_PLAN.md                     # план и статус миграции бот → Mini App
```

## Архитектурные правила

**Слои строго однонаправленны:** Domain ← Application ← Infrastructure ← Presentation.

- **Domain** — чистые dataclass-сущности и абстрактные репозитории. Никаких импортов из других слоёв.
- **Application** — use cases принимают репозитории через конструктор (dependency injection). Никакого ORM, никаких aiogram/FastAPI-типов.
- **Infrastructure** — реализации репозиториев, ORM-модели, внешние клиенты (CBU, APScheduler).
- **Presentation** — и API-роутеры, и бот-хендлеры только вызывают use cases через `container`. Никакого SQL/ORM напрямую.

## DI-контейнер

`Container` (`app/infrastructure/container.py`) создаётся на каждый запрос/апдейт и инжектируется через `data["container"]` (бот) или FastAPI dependency `ContainerDep` (API).

```python
# API (app/presentation/api/deps.py: ContainerDep)
async def endpoint(container: ContainerDep, user_id: CurrentUserId) -> ...:
    result = await container.add_expense.execute(dto)
```

Каждое свойство `Container` — это `@property`, возвращающий новый экземпляр use case с уже привязанными репозиториями.

## Добавление новой фичи

Новая функциональность для пользователя идёт через API + Mini App, не через бота:

1. **Domain:** добавить entity в `app/domain/entities/`, абстрактный репозиторий в `app/domain/repositories/`.
2. **Application:** создать use case в `app/application/use_cases/<группа>/`, DTO в `app/application/dto/`.
3. **Infrastructure:** реализовать репозиторий в `app/infrastructure/db/repositories/`, ORM-модель в `app/infrastructure/db/models/`.
4. **Container:** добавить `@property` в `Container` для нового use case.
5. **Migration:** `alembic revision --autogenerate -m "описание"`, проверить и применить.
6. **API:** роутер в `app/presentation/api/routers/`, pydantic-схемы в `schemas/`, подключить в `main.py`.
7. **Webapp:** экран/форма в `webapp/src/pages/`, маршрут в `webapp/src/app/router.tsx`. Схема клиента обновляется через `npm run generate:api` (нужен запущенный API).

## Миграции

```bash
alembic revision --autogenerate -m "название"   # создать
alembic upgrade head                             # применить
alembic downgrade -1                             # откатить
```

Файлы миграций — в `db/migrations/versions/`. Нумерация: `NNNN_описание.py`.

## Валюта

Все суммы хранятся в UZS (`Decimal`). USD конвертируется через `get_usd_rate()` (`app/infrastructure/currency/cbu_client.py`) в момент ввода — на уровне use case (`PrepareTransactionUseCase`), который и API, и (пока ещё частично) бот используют для расчёта UZS-эквивалента.

## Напоминания и планировщик

`APScheduler` запускается в `main.py`. Логика — в `app/infrastructure/notifications/scheduler.py`. Уведомление о платеже включает кнопку, открывающую соответствующее напоминание прямо в Mini App (`/reminders/{id}`).

## Тесты

```bash
pytest                    # запуск всех тестов (app/)
pytest -x                 # остановиться на первой ошибке
cd webapp && npx tsc -b --noEmit && npx oxlint src   # типы и линт фронтенда
```

Зависимости для тестов: `pytest`, `pytest-asyncio`, `pytest-mock`, `httpx`, `aiosqlite`.

## Зависимости

Python — через `pyproject.toml`:
```bash
pip install -e ".[dev]"
```

Frontend — через `webapp/package.json` (`npm install`; см. `webapp/.npmrc` про `legacy-peer-deps`).
