# Research: 002-compote-sales-tracker

**Дата**: 2026-05-04 (обновлено)
**Источник**: Context7 MCP (Принцип VI — обязательная проверка документации)

---

## 1. python-telegram-bot

**Решение**: v22.5 (текущая стабильная).

**Важное**: Конституция указывает «v20 (синхронный режим)», но v20+ требует
`async def handlers`. Бизнес-логика при этом остаётся синхронной.

**Подтверждённый API**:
```python
from telegram.ext import Application, CommandHandler, MessageHandler, filters

app = Application.builder().token("TOKEN").build()
app.add_handler(CommandHandler("day", day_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.run_polling()
```

**Паттерн**: `async def handler(update, context)` вызывает sync-сервисы напрямую.

---

## 2. SQLAlchemy 2.0 (sync ORM)

**Решение**: Полностью соответствует конституции.

**Подтверждённый API**:
```python
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine(DATABASE_URL)
with Session(engine) as session:
    stmt = select(Event).where(Event.event_date == target_date)
    events = session.scalars(stmt).all()
```

---

## 3. Anthropic SDK — структурированный вывод (парсинг событий)

**Решение**: `client.messages.parse(output_format=ParsedEvent)` — синхронный.

```python
import anthropic
from pydantic import BaseModel

client = anthropic.Anthropic()
result = client.messages.parse(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": user_text}],
    max_tokens=512,
    output_format=ParsedEvent,
)
event = result.parsed_output  # гарантированный тип ParsedEvent
```

---

## 4. Anthropic SDK — веб-поиск рыночной цены ← НОВОЕ

**Решение**: встроенный `web_search` инструмент (`type: "web_search_20250305"`).
Синхронный вызов, не требует внешних библиотек (requests, BeautifulSoup и т.д.).
Идеально соответствует Принципам I (простота) и II (LLM-first).

**Подтверждённый API**:
```python
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=256,
    messages=[{
        "role": "user",
        "content": (
            "Найди текущую среднюю цену натурального домашнего компота "
            "в Бишкеке, Кыргызстан за бутылку 0.5 литра. "
            "Ответь только числом в сомах."
        )
    }],
    tools=[{"name": "web_search", "type": "web_search_20250305"}],
)
market_price = float(response.content[-1].text.strip())
```

**Стратегия кеширования**:
- Результат сохраняется в `user_settings` с ключом `market_price_som`
  и датой последнего обновления `market_price_updated_at`.
- При запросе: если `market_price_updated_at` < сегодня → обновить, иначе взять кеш.
- При любой ошибке (API недоступен, не нашёл цену) → использовать кешированное
  значение или дефолт 80 сом.

**Альтернативы отклонены**:
- BeautifulSoup + requests: нужно поддерживать конкретные URL, которые меняются.
- Ручная команда `/setmarketprice`: снято требование пользователем.

---

## 5. Pydantic v2

**Решение**: `BaseModel` + `Field` + `Literal`. Без изменений.

**Новые схемы для ингредиентов**:
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import date

class ParsedIngredientPurchase(BaseModel):
    ingredient_name: str
    quantity: float
    unit: Literal["g", "kg", "ml", "l", "pcs"]
    total_price_som: float

class ParsedBatchUsage(BaseModel):
    usages: list[IngredientUsageItem]
    batch_volume_liters: Optional[float] = None  # None → бот уточнит

class IngredientUsageItem(BaseModel):
    ingredient_name: str
    quantity: float
    unit: Literal["g", "kg", "ml", "l", "pcs"]
```

---

## 6. gspread v6

**Решение**: без изменений. `service_account_from_dict()` + `append_row()`.

---

## 7. Расчёт себестоимости и рекомендованной цены

**Формулы** (бизнес-логика в `services/cost_calculator.py`):

```
стоимость_ингредиента = кол-во_использованного × цена_за_единицу_из_последней_закупки
суммарная_стоимость_партии = SUM(стоимость каждого ингредиента)
себестоимость_литра = суммарная_стоимость / объём_партии_в_литрах
себестоимость_бутылки = себестоимость_литра × 0.5

рекомендованная_цена = max(себестоимость_бутылки × 2, рыночная_цена × 0.9)
маржа = рекомендованная_цена - себестоимость_бутылки
```

**Рыночная цена по умолчанию**: 80 сом (если веб-поиск недоступен).

---

## 8. Инфраструктура

| Компонент | Решение |
|---|---|
| Хостинг | Fly.io (scale-to-zero) |
| БД | Neon PostgreSQL (scale-to-zero) |
| Секреты | `fly secrets set` |
| CI | pre-commit: ruff + black + isort |

---

## Сводная таблица Context7 (Шлюз VI)

| Библиотека | Актуальная версия | Ключевые находки |
|---|---|---|
| python-telegram-bot | v22.5 | Async handlers обязательны |
| SQLAlchemy | 2.0 | Sync ORM, `select()` + `Session.scalars()` |
| anthropic SDK (parse) | актуальный | `messages.parse(output_format=Model)` |
| anthropic SDK (search) | актуальный | `web_search_20250305` — встроенный sync |
| Pydantic | v2 | `BaseModel`, расширены схемы для ингредиентов |
| gspread | v6 | `service_account_from_dict()` + `append_row()` |
| alembic | актуальный | `autogenerate` + `upgrade head` |
