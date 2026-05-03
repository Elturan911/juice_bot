# Data Model: 002-compote-sales-tracker

**Дата**: 2026-05-04 (обновлено — добавлены таблицы ингредиентов)

---

## Таблицы БД (PostgreSQL / Neon)

### events

Основная таблица — продажи, размещения, просрочки, ручные остатки.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| id | INTEGER | PK, autoincrement | — |
| event_type | VARCHAR(30) | NOT NULL | см. EventType ниже |
| floor | INTEGER | NULL | номер этажа |
| quantity | INTEGER | NULL | количество бутылок |
| bottle_volume_ml | INTEGER | NULL | объём бутылки в мл (500 по умолчанию) |
| amount_som | NUMERIC(10,2) | NULL | сумма в сомах |
| description | TEXT | NULL | описание (для расходов) |
| raw_text | TEXT | NOT NULL | исходный текст |
| event_date | DATE | NOT NULL | дата события (UTC+6) |
| created_at | TIMESTAMP | NOT NULL, default=now() | дата записи |

**Индекс**: `event_date`.

---

### ingredients

Справочник ингредиентов.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| id | INTEGER | PK, autoincrement | — |
| name | VARCHAR(100) | UNIQUE, NOT NULL | название (нормализованное, строчные) |
| base_unit | VARCHAR(5) | NOT NULL | базовая единица: g / ml / pcs |
| latest_price_per_unit | NUMERIC(12,4) | NULL | цена за 1 base_unit (из последней закупки) |
| updated_at | TIMESTAMP | NOT NULL, default=now() | дата последней закупки |

**Логика нормализации**: «Сахар», «сахар», «САХАР» → «сахар». Единица хранения
всегда в наименьшей (г, мл), конвертация при записи (кг→г, л→мл).

---

### ingredient_purchases

История закупок ингредиентов.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| id | INTEGER | PK, autoincrement | — |
| ingredient_id | INTEGER | FK → ingredients.id, NOT NULL | ингредиент |
| quantity_g_or_ml | NUMERIC(12,3) | NOT NULL | кол-во в базовой единице (г или мл) |
| total_price_som | NUMERIC(10,2) | NOT NULL | итоговая стоимость закупки |
| price_per_unit | NUMERIC(12,6) | NOT NULL | сом за 1 г/мл (авторасчёт) |
| raw_text | TEXT | NOT NULL | исходный текст |
| purchase_date | DATE | NOT NULL | дата закупки |
| created_at | TIMESTAMP | NOT NULL, default=now() | — |

---

### batches

Партия компота — результат варки.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| id | INTEGER | PK, autoincrement | — |
| batch_date | DATE | NOT NULL | дата варки |
| volume_liters | NUMERIC(6,2) | NOT NULL | объём партии в литрах |
| total_ingredient_cost_som | NUMERIC(10,2) | NULL | стоимость ингредиентов (авторасчёт) |
| cost_per_liter_som | NUMERIC(10,2) | NULL | себестоимость 1 л |
| cost_per_bottle_som | NUMERIC(10,2) | NULL | себестоимость 0.5 л бутылки |
| recommended_price_som | NUMERIC(10,2) | NULL | рекомендованная цена продажи |
| market_price_used_som | NUMERIC(10,2) | NULL | рыночная цена на момент расчёта |
| raw_text | TEXT | NOT NULL | исходный текст |
| created_at | TIMESTAMP | NOT NULL, default=now() | — |

---

### batch_ingredient_usages

Расход ингредиентов на конкретную партию.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| id | INTEGER | PK, autoincrement | — |
| batch_id | INTEGER | FK → batches.id, NOT NULL | партия |
| ingredient_id | INTEGER | FK → ingredients.id, NOT NULL | ингредиент |
| quantity_g_or_ml | NUMERIC(12,3) | NOT NULL | использовано (в г/мл) |
| price_per_unit_used | NUMERIC(12,6) | NOT NULL | цена на момент расчёта (из посл. закупки) |
| cost_som | NUMERIC(10,2) | NOT NULL | стоимость этого ингредиента в партии |

---

### user_settings

Настройки и кеш.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| id | INTEGER | PK, autoincrement | — |
| key | VARCHAR(50) | UNIQUE, NOT NULL | ключ |
| value | TEXT | NOT NULL | значение |
| updated_at | TIMESTAMP | NOT NULL, default=now() | — |

**Записи**:

| key | Описание | Пример |
|---|---|---|
| `bottle_price` | Цена продажи 1 бутылки | `100` |
| `market_price_som` | Кешированная рыночная цена (сом/0.5л) | `120` |
| `market_price_updated_at` | Дата последнего обновления рыночной цены | `2026-05-04` |
| `spreadsheet_id` | ID Google Таблицы | `1BxiM...` |
| `pending_batch_text` | Временное хранение текста партии ожидающей объём | `на партию ушло...` |

---

## SQLAlchemy модели (сводка)

```python
# Упрощённый вид; полный код в src/models/

class Event(Base):         # events
class Ingredient(Base):    # ingredients
class IngredientPurchase(Base):  # ingredient_purchases
class Batch(Base):         # batches
class BatchIngredientUsage(Base): # batch_ingredient_usages
class UserSetting(Base):   # user_settings
```

---

## Pydantic схемы для LLM-вывода

**Архитектура (C2 fix)**: ОДИН вызов `messages.parse(output_format=ParsedMessage)` —
единая схема покрывает все 8 типов событий. Нет множественных LLM-вызовов.
Routing происходит в Python по полю `event_type`.

```python
# src/services/parser.py

class EventType(str, Enum):
    PLACEMENT = "placement"
    SALE = "sale"
    EXPIRY_REMOVAL = "expiry_removal"
    MANUAL_COUNT = "manual_count"
    PRODUCTION_EXPENSE = "production_expense"
    INGREDIENT_PURCHASE = "ingredient_purchase"   # только если кол-во в ед. И цена
    BATCH_USAGE = "batch_usage"
    UNKNOWN = "unknown"

class IngredientUsageItem(BaseModel):
    ingredient_name: str
    quantity: float
    unit: Literal["g", "kg", "ml", "l", "pcs"]

class MarketPriceResult(BaseModel):
    price_som: float          # для Pydantic-парсинга web_search ответа

# Единая схема для всех типов событий
class ParsedMessage(BaseModel):
    event_type: EventType

    # Поля для placement / sale / expiry_removal / manual_count
    floor: Optional[int] = None
    quantity: Optional[int] = None
    bottle_volume_ml: Optional[int] = None     # H4 fix
    amount_som: Optional[float] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    additional_events: Optional[list["ParsedMessage"]] = None  # несколько этажей

    # Поля для ingredient_purchase
    ingredient_name: Optional[str] = None
    ingredient_quantity: Optional[float] = None
    ingredient_unit: Optional[Literal["g", "kg", "ml", "l", "pcs"]] = None
    ingredient_total_price_som: Optional[float] = None

    # Поля для batch_usage
    batch_usages: Optional[list[IngredientUsageItem]] = None
    batch_volume_liters: Optional[float] = None
```

**Промпт-правило** (H2 fix — в системном промпте parse_message):
> `ingredient_purchase` — ТОЛЬКО если сообщение содержит И количество в единицах
> (кг/г/л/мл/шт) И цену. Пример: «купил сахар 2 кг за 200 сом».
> Если цена без количества или количество без цены → `production_expense`.

---

## Расчёт себестоимости (бизнес-логика)

```
для каждого ингредиента i в партии:
    cost_i = quantity_used_g × ingredient.latest_price_per_unit

total_cost = SUM(cost_i для всех i)
cost_per_liter = total_cost / batch_volume_liters
cost_per_bottle = cost_per_liter × 0.5

market_price = get_or_fetch_market_price()  # кеш / web_search / 80 сом
recommended_price = max(cost_per_bottle × 2, market_price × 0.9)
margin = recommended_price - cost_per_bottle
```

---

## Google Sheets — структура листов

### Лист «Выручка»
| Дата | Этаж | Бутылок | Выручка (сом) |
|---|---|---|---|

### Лист «Расходы»
| Дата | Тип | Описание | Сумма (сом) |
|---|---|---|---|

### Лист «Прибыль»
| Дата | Выручка (сом) | Расходы (сом) | Прибыль (сом) |
|---|---|---|---|
