# 💰 Wallet Bot

Telegram-бот для личных финансов: учёт доходов/расходов, бюджеты, долги, копилка, рассрочки.

## Стек

- Python 3.11+, aiogram 3, PostgreSQL, SQLAlchemy (async), Alembic, Docker

## Быстрый старт

```bash
cp .env.example .env
# Заполните .env: BOT_TOKEN, POSTGRES_PASSWORD и т.д.

docker-compose up --build
```

Бот запустится, автоматически применит миграции и начнёт работу.

## Локальная разработка

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Запустить PostgreSQL отдельно, затем:
alembic upgrade head
python main.py
```

## Архитектура

```
Domain → Application → Infrastructure → Presentation
```

Подробнее: [CLAUDE.md](CLAUDE.md)

## Функциональность

| Функция        | Статус |
|----------------|--------|
| Расходы        | ✅     |
| Доходы         | ✅     |
| Баланс         | ✅     |
| Категории      | ✅     |
| Бюджеты        | ✅     |
| Отчёты         | ✅     |
| Долги          | ✅     |
| Копилка        | ✅     |
| Рассрочки      | ✅     |
| CSV экспорт    | ✅     |
| Excel экспорт  | ✅     |
| Напоминания    | ✅     |
