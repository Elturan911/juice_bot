<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan

## Active Feature: 002-compote-sales-tracker

**Plan**: specs/002-compote-sales-tracker/plan.md
**Spec**: specs/002-compote-sales-tracker/spec.md

## Stack (verified via Context7 2026-05-04)

- Python 3.11+, Poetry
- python-telegram-bot v22.5 (handlers async def, business logic sync)
- anthropic SDK sync — messages.parse(output_format=Model) для событий;
  messages.create(tools=[web_search_20250305]) для рыночной цены (1 раз в сутки)
- SQLAlchemy 2.0 sync ORM + psycopg2-binary + alembic
- Pydantic v2 — BaseModel, Field, Literal
- gspread v6 — service_account_from_dict() + append_row()
- ruff + black + isort (enforced)
- Fly.io + Neon PostgreSQL (scale-to-zero)

## Project Structure

```
src/
├── bot.py
├── models/       # base.py, event.py, ingredient.py, ingredient_purchase.py,
│                 # batch.py, batch_usage.py, settings.py
├── services/     # parser.py, analytics.py, sheets.py,
│                 # cost_calculator.py, market_price.py
└── handlers/     # messages.py, commands.py
tests/
alembic/
```

## Market Price Logic

- Ищется автоматически через Claude web_search (1 раз в сутки)
- Кешируется в user_settings: market_price_som + market_price_updated_at
- По умолчанию (если недоступно): 80 сом
- Формула: recommended = max(cost_per_bottle × 2, market_price × 0.9)

## Commands

```bash
poetry install
poetry run alembic upgrade head
poetry run python src/bot.py
poetry run pytest tests/ -v
poetry run ruff check src/
```

## Secrets (never in code)

Local: .env file
Production: fly secrets set KEY=VALUE
<!-- SPECKIT END -->
