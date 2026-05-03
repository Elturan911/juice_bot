# Quickstart: juice_bot (компот-трекер)

**Дата**: 2026-05-04

Этот файл описывает как запустить бота локально и задеплоить на Fly.io.

---

## Предварительные требования

- Python 3.11+
- Poetry (`pip install poetry`)
- PostgreSQL (локально) **или** строка подключения к Neon
- Telegram-бот, созданный через @BotFather (получить TOKEN)
- Google Cloud сервисный аккаунт с доступом к Google Sheets API
- Google Таблица с листами «Выручка», «Расходы», «Прибыль» (создать вручную)

---

## Локальный запуск

### 1. Установить зависимости

```bash
cd juice_bot
poetry install
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
# Заполнить значения в .env:
```

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:pass@localhost:5432/juicebot
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here
```

### 3. Применить миграции БД

```bash
poetry run alembic upgrade head
```

### 4. Запустить бота

```bash
poetry run python src/bot.py
```

### 5. Проверить работу

Открыть Telegram → найти бота → отправить:
1. `/setprice 100` — установить цену
2. «Разместил 15 бутылок на 2ом этаже» — должен ответить подтверждением
3. «Продал 10 бутылок на 2ом этаже» — должен ответить с выручкой 1000 сом
4. `/day` — должен показать дневной отчёт
5. Открыть Google Таблицу — проверить строки в листах

---

## Деплой на Fly.io

### 1. Установить fly CLI

```bash
brew install flyctl
fly auth login
```

### 2. Создать приложение (один раз)

```bash
fly apps create juice-bot
```

### 3. Установить секреты

```bash
fly secrets set TELEGRAM_BOT_TOKEN="..."
fly secrets set DATABASE_URL="..."
fly secrets set ANTHROPIC_API_KEY="..."
fly secrets set GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
fly secrets set GOOGLE_SPREADSHEET_ID="..."
```

### 4. Применить миграции на продакшн БД

```bash
fly ssh console --app juice-bot -C "poetry run alembic upgrade head"
```

### 5. Задеплоить

```bash
fly deploy
```

### 6. Проверить логи

```bash
fly logs --app juice-bot
```

---

## Структура `.env.example`

```env
TELEGRAM_BOT_TOKEN=
DATABASE_URL=postgresql://user:pass@host:5432/dbname
ANTHROPIC_API_KEY=
GOOGLE_SERVICE_ACCOUNT_JSON=
GOOGLE_SPREADSHEET_ID=
```

---

## Запуск тестов

```bash
cd src
poetry run pytest tests/ -v
```

Тесты запускаются против реальной тестовой БД (не моков), указанной через
`DATABASE_URL` в `.env`.

---

## Проверка линтера

```bash
poetry run ruff check src/
poetry run black --check src/
poetry run isort --check-only src/
```
