# Implementation Plan: Учёт продаж компота — Telegram-бот

**Branch**: `002-compote-sales-tracker` | **Date**: 2026-05-04 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-compote-sales-tracker/spec.md`

## Summary

Telegram-бот для единственного владельца стартапа по продаже натурального компота
в офисе банка. Принимает свободный текст на русском, парсит 6 типов событий через
Anthropic Claude (`messages.parse` + Pydantic). Хранит события и ингредиенты в
PostgreSQL (Neon). Дублирует в Google Sheets (3 листа). Рассчитывает себестоимость
партии из учёта ингредиентов и предлагает рекомендованную цену, сравнивая с рыночной
ценой компота в Бишкеке (ищется автоматически через встроенный Claude `web_search`
раз в сутки). Хостинг: Fly.io (scale-to-zero), цель <$5/мес.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- python-telegram-bot v22.5 (async handlers, sync business logic)
- anthropic SDK sync — `messages.parse(output_format=Model)` для парсинга событий;
  `messages.create(tools=[web_search])` для поиска рыночной цены
- SQLAlchemy 2.0 sync ORM + psycopg2-binary + alembic
- Pydantic v2 — схемы для LLM-вывода
- gspread v6 — `service_account_from_dict()` + `append_row()`
- black + isort + ruff (enforced)

**Storage**: PostgreSQL на Neon (scale-to-zero)
**Testing**: pytest + реальная тестовая БД (Принцип «Тестирование и надёжность»)
**Target Platform**: Fly.io Linux (Docker)
**Performance Goals**: ответ <5 с, <$5/мес, поиск рыночной цены не чаще 1 раза в сутки
**Constraints**: 1 пользователь, только KGS, только русский язык
**Scale/Scope**: ~10–50 событий/день, ~5–10 закупок ингредиентов в месяц

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Шлюз 0: Проверка документации через Context7 (Принцип VI — ОБЯЗАТЕЛЬНО)

| Библиотека | Версия подтверждена через Context7 | Ключевые изменения API |
|---|---|---|
| python-telegram-bot | ✅ v22.5 | Handlers `async def`; PTB управляет event loop |
| SQLAlchemy | ✅ 2.0 | `select()` + `Session.scalars()`, `mapped_column` |
| anthropic SDK (parse) | ✅ актуальный | `client.messages.parse(output_format=Model)` |
| anthropic SDK (search) | ✅ актуальный | `tools=[{"name":"web_search","type":"web_search_20250305"}]` |
| Pydantic v2 | ✅ актуальный | `BaseModel`, `Field`, `Literal`, `Optional` |
| gspread | ✅ v6 | `service_account_from_dict()` + `append_row()` |
| alembic | ✅ актуальный | `autogenerate` + `upgrade head` |

### Шлюз 1: Принципы конституции

| Принцип | Статус | Примечание |
|---|---|---|
| I. Простота и синхронность | ✅ с оговоркой | Handlers async (PTB), вся бизнес-логика sync |
| II. LLM-первичный разбор | ✅ | `messages.parse(output_format=ParsedEvent)` |
| III. Обязательный стек | ✅ | PTB v22.5; требует PATCH-поправки к конституции |
| IV. Строгое качество кода | ✅ | ruff + black + isort в pre-commit |
| V. Безопасность | ✅ | `.env` локально, `fly secrets` на проде |
| VI. Context7 | ✅ | Все 7 библиотек проверены выше |
| VII. Экономная инфраструктура | ✅ | Fly.io + Neon, scale-to-zero |

## Complexity Tracking

| Нарушение | Почему нужно | Почему альтернатива не подходит |
|---|---|---|
| Async handlers в PTB v22.5 | PTB v20+ требует async; старый sync API удалён | PTB v13 (sync) не поддерживается с 2023 г. |
| Два типа LLM-вызовов (parse + web_search) | parse — для NLU; web_search — для поиска рыночной цены | Один вызов не покрывает оба сценария |

## Project Structure

### Documentation (this feature)

```text
specs/002-compote-sales-tracker/
├── plan.md              ← этот файл
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── bot_commands.md
└── tasks.md             ← /speckit-tasks (не создан командой plan)
```

### Source Code (repository root)

```text
src/
├── bot.py                        # точка входа: Application, handlers, run_polling
├── models/
│   ├── __init__.py
│   ├── base.py                   # create_engine, Session, DeclarativeBase
│   ├── event.py                  # Event — продажи, размещения, просрочки и т.д.
│   ├── ingredient.py             # Ingredient — справочник ингредиентов
│   ├── ingredient_purchase.py    # IngredientPurchase — закупки
│   ├── batch.py                  # Batch — партии компота
│   ├── batch_usage.py            # BatchIngredientUsage — расход ингредиентов
│   └── settings.py               # UserSetting — цена бутылки, кеш рыночной цены
├── services/
│   ├── __init__.py
│   ├── parser.py                 # LLM-парсинг событий → ParsedEvent (Pydantic)
│   ├── analytics.py              # аналитика за день/неделю/месяц
│   ├── cost_calculator.py        # расчёт себестоимости партии
│   ├── market_price.py           # веб-поиск рыночной цены (Claude web_search, 1/сутки)
│   └── sheets.py                 # gspread интеграция (3 листа)
└── handlers/
    ├── __init__.py
    ├── messages.py               # обработчик свободного текста
    └── commands.py               # /setprice, /day, /week, /month, /sheet, /cost, /help

alembic/
├── env.py
└── versions/
    ├── 0001_initial_schema.py
    └── 0002_add_ingredients.py

tests/
├── integration/
│   ├── test_parser.py            # LLM-парсинг (реальный API)
│   ├── test_analytics.py         # аналитика (реальная тестовая БД)
│   └── test_cost_calculator.py   # расчёт себестоимости
└── unit/
    └── test_calculations.py      # расчёт прибыли и рекомендованной цены

.env.example
Dockerfile
fly.toml
pyproject.toml
alembic.ini
```

**Structure Decision**: Single project. Добавлен модуль `services/cost_calculator.py`
для расчёта себестоимости и `services/market_price.py` для веб-поиска цены. Четыре
новые модели для учёта ингредиентов.
