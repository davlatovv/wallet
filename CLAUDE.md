# Wallet Bot — CLAUDE.md

Telegram-бот для личных финансов. Python 3.11+, aiogram 3, PostgreSQL, SQLAlchemy async, Alembic, APScheduler, Docker.

## Запуск

```bash
docker-compose up --build      # полный запуск (PostgreSQL + бот)
python main.py                 # локально (нужен .env с BOT_TOKEN и DATABASE_URL)
```

`.env` обязателен. Переменные: `BOT_TOKEN`, `DATABASE_URL` (asyncpg-формат: `postgresql+asyncpg://...`), опционально `LOG_LEVEL`, `TIMEZONE`, `DEBUG`.

Миграции применяются автоматически при старте через `alembic upgrade head` (subprocess в `main.py:run_migrations`).

## Структура

```
main.py                                  # точка входа, запуск бота и APScheduler
app/
  config/settings.py                     # pydantic-settings, читает .env
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
    notifications/scheduler.py           # APScheduler: напоминания
  presentation/telegram/
    handlers/                            # aiogram-хендлеры (по одному файлу на фичу)
    middlewares/
      db_session.py                      # открывает сессию + создаёт Container
      register_user.py                   # авто-регистрация пользователя
    keyboards/                           # inline и reply-клавиатуры
    states/                              # FSMState-классы
    router.py                            # подключает все хендлеры
db/
  migrations/versions/                   # Alembic-миграции
```

## Архитектурные правила

**Слои строго однонаправленны:** Domain ← Application ← Infrastructure ← Presentation.

- **Domain** — чистые dataclass-сущности и абстрактные репозитории. Никаких импортов из других слоёв.
- **Application** — use cases принимают репозитории через конструктор (dependency injection). Никакого ORM, никаких aiogram-типов.
- **Infrastructure** — реализации репозиториев, ORM-модели, внешние клиенты (CBU, APScheduler).
- **Presentation** — хендлеры только вызывают use cases через `container`. Никакого SQL/ORM в хендлерах.

## DI-контейнер

`Container` (`app/infrastructure/container.py`) создаётся в `DbSessionMiddleware` на каждый запрос и инжектируется в хендлеры через `data["container"]`.

```python
# Получение в хендлере (автоматически через middleware)
async def handler(message: Message, container: Container) -> None:
    result = await container.add_expense.execute(dto)
```

Каждое свойство `Container` — это `@property`, возвращающий новый экземпляр use case с уже привязанными репозиториями.

## Добавление новой фичи

1. **Domain:** добавить entity в `app/domain/entities/`, абстрактный репозиторий в `app/domain/repositories/`.
2. **Application:** создать use case в `app/application/use_cases/<группа>/`, DTO в `app/application/dto/`.
3. **Infrastructure:** реализовать репозиторий в `app/infrastructure/db/repositories/`, ORM-модель в `app/infrastructure/db/models/`.
4. **Container:** добавить `@property` в `Container` для нового use case.
5. **Migration:** `alembic revision --autogenerate -m "описание"`, проверить и применить.
6. **Presentation:** создать хендлер в `app/presentation/telegram/handlers/`, FSM-состояния в `states/`, подключить роутер в `router.py`.

## Миграции

```bash
alembic revision --autogenerate -m "название"   # создать
alembic upgrade head                             # применить
alembic downgrade -1                             # откатить
```

Файлы миграций — в `db/migrations/versions/`. Нумерация: `NNNN_описание.py`.

## Валюта

Все суммы хранятся в UZS (`Decimal`). USD конвертируется через `get_usd_rate()` (`app/infrastructure/currency/cbu_client.py`) в момент ввода, затем сохраняется UZS-эквивалент.

## Напоминания и планировщик

`APScheduler` запускается в `main.py`. Логика — в `app/infrastructure/notifications/scheduler.py`. При старте планировщик подгружает активные напоминания из БД и ставит джобы.

## Тесты

```bash
pytest                    # запуск всех тестов
pytest -x                 # остановиться на первой ошибке
```

Зависимости для тестов: `pytest`, `pytest-asyncio`, `pytest-mock`.

## Зависимости

Управляются через `pyproject.toml`. Установка:
```bash
pip install -e ".[dev]"
```
