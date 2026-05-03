---
description: "Task list for 002-compote-sales-tracker"
---

# Tasks: Учёт продаж компота — Telegram-бот

**Input**: Design documents from `/specs/002-compote-sales-tracker/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Организация**: задачи сгруппированы по user story для независимой реализации и тестирования.

---

## Phase 0: Проверка документации Context7 (Принцип VI)

**Статус**: ✅ ВЫПОЛНЕНО в ходе /speckit.plan

Все 7 библиотек проверены через Context7 и зафиксированы в plan.md → Constitution Check.

---

## Phase 1: Setup (Базовая структура проекта)

**Цель**: создать рабочий скелет проекта, установить зависимости.

- [ ] T001 Инициализировать Poetry-проект и создать `pyproject.toml` с зависимостями: python-telegram-bot==22.5, anthropic, sqlalchemy, psycopg2-binary, alembic, pydantic>=2, gspread, python-dotenv
- [ ] T002 [P] Настроить ruff, black, isort в `pyproject.toml` (секции [tool.ruff], [tool.black], [tool.isort])
- [ ] T003 [P] Создать `.env.example` с переменными: TELEGRAM_BOT_TOKEN, DATABASE_URL, ANTHROPIC_API_KEY, GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SPREADSHEET_ID
- [ ] T004 [P] Создать структуру директорий: `src/models/`, `src/services/`, `src/handlers/`, `tests/integration/`, `tests/unit/`, `alembic/versions/`
- [ ] T005 [P] Создать `Dockerfile` (python:3.11-slim, poetry install --no-dev, CMD poetry run python src/bot.py)
- [ ] T006 [P] Создать `fly.toml` (app=juice-bot, region=sin, vm.memory=256mb, vm.cpu_kind=shared)

---

## Phase 2: Foundation (Блокирующие зависимости)

**Цель**: БД, базовые модели, точка входа бота — необходимы для ВСЕХ user stories.

**⚠️ КРИТИЧНО**: ни одна user story не может начаться до завершения этой фазы.

- [ ] T007 Создать `src/models/base.py`: `create_engine(DATABASE_URL)`, `Session = sessionmaker(engine)`, `class Base(DeclarativeBase)`
- [ ] T008 [P] Создать `src/models/event.py`: класс `Event(Base)` с полями id, event_type (VARCHAR 30), floor, quantity, bottle_volume_ml (INTEGER NULL), amount_som, description, raw_text, event_date, created_at; индекс по event_date
- [ ] T009 [P] Создать `src/models/settings.py`: класс `UserSetting(Base)` с полями id, key (UNIQUE), value, updated_at; функции `get_setting(session, key)` и `set_setting(session, key, value)`
- [ ] T010 Инициализировать Alembic: `alembic init alembic`, настроить `alembic/env.py` (импорт Base из src/models/base.py, DATABASE_URL из env)
- [ ] T011 Создать первую миграцию `alembic/versions/0001_initial_schema.py` через `alembic revision --autogenerate -m "initial"` (таблицы events, user_settings)
- [ ] T012 Создать `src/bot.py`: `Application.builder().token(TOKEN).build()`, `app.run_polling()`; заглушки для add_handler (заполнятся в следующих фазах)
- [ ] T013 Создать `src/handlers/__init__.py`, `src/services/__init__.py`, `src/models/__init__.py` (пустые)

**Checkpoint**: `alembic upgrade head` выполняется без ошибок; `python src/bot.py` запускается.

---

## Phase 3: User Story 1 — Запись события в свободной форме (P1) 🎯 MVP

**Цель**: пользователь пишет в свободной форме → бот парсит через LLM → сохраняет → отвечает.

**Независимый тест**: отправить 5 сообщений разных типов (размещение, продажа, просрочка, расходы, непонятное) — каждое должно дать правильный ответ.

### Реализация US1

- [ ] T014 [P] [US1] Создать единую Pydantic-схему `ParsedMessage` в `src/services/parser.py` (C2+H1+H4 fix): EventType enum (8 типов: placement/sale/expiry_removal/manual_count/production_expense/ingredient_purchase/batch_usage/unknown); класс `ParsedMessage` с полями: event_type, floor, quantity, bottle_volume_ml, amount_som, description, event_date, additional_events (для нескольких этажей), ingredient_name, ingredient_quantity, ingredient_unit, ingredient_total_price_som, batch_usages: list[IngredientUsageItem], batch_volume_liters; вспомогательный `IngredientUsageItem`; `MarketPriceResult(price_som: float)` для web_search
- [ ] T015 [US1] Реализовать `parse_message(text: str) -> ParsedMessage` в `src/services/parser.py`: ОДИН вызов `client.messages.parse(output_format=ParsedMessage, ...)` покрывает все типы событий; системный промпт на русском с правилом разграничения ingredient_purchase vs production_expense (H2 fix: «ingredient_purchase ТОЛЬКО если указаны И количество в ед. И цена») и 6 few-shot примерами из spec.md; handle additional_events для сообщений с несколькими этажами
- [ ] T016 [US1] Реализовать `save_event(session, parsed: ParsedEvent) -> Event` в `src/models/event.py`: создание Event, session.add(), session.commit(), возврат объекта
- [ ] T017 [US1] Создать `src/handlers/messages.py`: `async def handle_message(update, context)` — вызывает parse_message() → save_event() → отправляет подтверждение; для unknown — отправляет пример корректного ввода
- [ ] T018 [US1] Зарегистрировать `MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)` в `src/bot.py`

**Checkpoint**: US1 полностью функционален и тестируем независимо.

---

## Phase 4: User Story 4 — Установка цены бутылки (P2, блокирует US2)

**Цель**: `/setprice 100` → цена сохранена → аналитика может считать выручку.

**Независимый тест**: `/setprice 100` → бот подтверждает; записать продажу → выручка посчитана; повторный `/setprice 120` → цена обновлена.

### Реализация US4

- [ ] T019 [P] [US4] Создать `src/handlers/commands.py`: `async def setprice_handler(update, context)` — парсит аргумент как float, вызывает set_setting(session, "bottle_price", value), отвечает подтверждением; ошибка при неверном формате
- [ ] T020 [US4] Добавить в `src/handlers/messages.py` проверку цены перед сохранением события типа "sale": если bottle_price не установлена — отвечает «Сначала установи цену: /setprice 100» и НЕ сохраняет событие
- [ ] T021 [US4] Зарегистрировать `CommandHandler("setprice", setprice_handler)` в `src/bot.py`

**Checkpoint**: `/setprice 100` работает; попытка записать продажу без цены → напоминание.

---

## Phase 5: User Story 2 — Аналитика за день (P2)

**Цель**: `/day 2026-05-04` → полный отчёт с детализацией по этажам.

**Независимый тест**: записать события через US1, установить цену через US4, вызвать `/day` — цифры совпадают с ожидаемыми.

### Реализация US2

- [ ] T022 [P] [US2] Реализовать `get_day_analytics(session, target_date: date) -> dict` в `src/services/analytics.py`: SELECT из events WHERE event_date=date; GROUP BY floor для продаж; суммирование выручки (quantity × bottle_price), расходов, прибыли
- [ ] T023 [US2] Реализовать `format_day_report(analytics: dict, date: date) -> str` в `src/services/analytics.py`: формирует текст отчёта с emoji, детализацией по этажам, итогами
- [ ] T024 [US2] Создать `async def day_handler(update, context)` в `src/handlers/commands.py`: парсит опциональную дату из аргумента (default=сегодня), вызывает get_day_analytics(), format_day_report(), отправляет результат
- [ ] T025 [US2] Зарегистрировать `CommandHandler("day", day_handler)` в `src/bot.py`

**Checkpoint**: `/day` и `/day 2026-05-04` возвращают корректный отчёт с детализацией по этажам.

---

## Phase 6: User Story 3 — Аналитика за неделю и месяц (P3)

**Цель**: `/week ДАТА` и `/month ГГГГ-ММ` → агрегированные отчёты.

**Независимый тест**: записать данные за 7 дней, `/week` — суммы соответствуют.

### Реализация US3

- [ ] T026 [P] [US3] Реализовать `get_week_analytics(session, any_date: date) -> dict` в `src/services/analytics.py`: вычислить понедельник/воскресенье недели по ISO, SELECT WHERE event_date BETWEEN mon AND sun
- [ ] T027 [P] [US3] Реализовать `get_month_analytics(session, year: int, month: int) -> dict` в `src/services/analytics.py`: SELECT WHERE EXTRACT(year)=year AND EXTRACT(month)=month
- [ ] T028 [US3] Создать `async def week_handler(update, context)` в `src/handlers/commands.py`; зарегистрировать в `src/bot.py`
- [ ] T029 [US3] Создать `async def month_handler(update, context)` в `src/handlers/commands.py`; зарегистрировать в `src/bot.py`

**Checkpoint**: `/week` и `/month` с датой и без возвращают корректные агрегаты.

---

## Phase 7: User Story 5 — Google Sheets интеграция (P3)

**Цель**: после каждого события → строка в нужном листе таблицы.

**Независимый тест**: записать продажу → открыть Google Таблицу → строка в «Выручка».

### Реализация US5

- [ ] T030 [P] [US5] Создать `src/services/sheets.py`: `get_sheets_client()` → `gspread.service_account_from_dict(json.loads(GOOGLE_SERVICE_ACCOUNT_JSON))`; `get_spreadsheet()` → `client.open_by_key(GOOGLE_SPREADSHEET_ID)`
- [ ] T031 [P] [US5] Реализовать `append_to_revenue(sheet, date, floor, quantity, amount)` в `src/services/sheets.py`: `worksheet("Выручка").append_row([...])`
- [ ] T032 [P] [US5] Реализовать `append_to_expenses(sheet, date, type_, description, amount)` в `src/services/sheets.py`
- [ ] T033 [P] [US5] Реализовать `append_to_profit(sheet, date, revenue, expenses, profit)` в `src/services/sheets.py`
- [ ] T034 [US5] Добавить try/except вокруг всех Sheets-вызовов в `src/services/sheets.py`: при ошибке логировать, возвращать False; вызывающий код уведомляет пользователя
- [ ] T035 [US5] Интегрировать вызовы sheets в `src/handlers/messages.py`: после save_event() → вызов нужного append_* в зависимости от event_type; при False — добавить к ответу «⚠️ В таблицу не добавилось»
- [ ] T036 [US5] Создать `async def sheet_handler(update, context)` в `src/handlers/commands.py`; зарегистрировать в `src/bot.py`

**Checkpoint**: запись события → строка в Google Sheets; при недоступности Sheets — данные в БД сохранены, уведомление пользователю.

---

## Phase 8: User Story 6 — Учёт закупки ингредиентов (P3)

**Цель**: «купил сахар 2 кг за 200 сом» → сохранено, цена за грамм рассчитана.

**Независимый тест**: 2 закупки разных ингредиентов → оба сохранены с правильной ценой за единицу.

### Реализация US6

- [ ] T037 [P] [US6] Создать `src/models/ingredient.py`: класс `Ingredient(Base)` с полями id, name (UNIQUE), base_unit, latest_price_per_unit, updated_at; функция `get_or_create_ingredient(session, name, unit) -> Ingredient`; нормализация имени (lower().strip())
- [ ] T038 [P] [US6] Создать `src/models/ingredient_purchase.py`: класс `IngredientPurchase(Base)` с полями id, ingredient_id (FK), quantity_g_or_ml, total_price_som, price_per_unit, raw_text, purchase_date, created_at
- [ ] T039 [US6] Создать миграцию `alembic/versions/0002_add_ingredients.py` через `alembic revision --autogenerate -m "add ingredients"` (таблицы ingredients, ingredient_purchases)
- [ ] T040 [P] [US6] Убедиться что `ParsedMessage` (T014) уже содержит поля ingredient_name, ingredient_quantity, ingredient_unit, ingredient_total_price_som — дополнительная схема не нужна (C2 fix)
- [ ] T041 [US6] Создать утилиту `convert_to_base_unit(quantity: float, unit: str) -> float` в `src/services/unit_converter.py` (M1 fix): кг→г ×1000, л→мл ×1000, г и мл — без изменений; импортировать в T042 и T049
- [ ] T042 [US6] Реализовать `save_ingredient_purchase(session, parsed: ParsedMessage) -> IngredientPurchase` в `src/models/ingredient_purchase.py`: использовать `unit_converter.convert_to_base_unit()` для конвертации; обновить `ingredient.latest_price_per_unit`; commit
- [ ] T043 [US6] Добавить routing в `src/handlers/messages.py` для event_type=`ingredient_purchase`: parsed = parse_message(text); если ingredient_purchase → save_ingredient_purchase(session, parsed) → ответ с ценой за единицу; (C2 fix — используем уже имеющийся ParsedMessage)

**Checkpoint**: закупка сохранена, `ingredient.latest_price_per_unit` обновлена; повторная закупка — цена обновляется с уведомлением.

---

## Phase 9: User Story 7 — Расчёт себестоимости и рекомендованная цена (P3)

**Цель**: «на партию ушло 500 г сахара и 2 кг яблок, сварил 10 литров» → себестоимость + рекомендованная цена с рыночным сравнением.

**Независимый тест**: закупить ингредиенты (US6) → записать расход → проверить цифры и рекомендацию.

### Реализация US7

- [ ] T044 [P] [US7] Создать `src/models/batch.py`: класс `Batch(Base)` с полями id, batch_date, volume_liters, total_ingredient_cost_som, cost_per_liter_som, cost_per_bottle_som, recommended_price_som, market_price_used_som, raw_text, created_at
- [ ] T045 [P] [US7] Создать `src/models/batch_usage.py`: класс `BatchIngredientUsage(Base)` с полями id, batch_id (FK), ingredient_id (FK), quantity_g_or_ml, price_per_unit_used, cost_som
- [ ] T046 [P] [US7] Убедиться что `ParsedMessage` (T014) содержит `batch_usages: list[IngredientUsageItem]` и `batch_volume_liters: Optional[float]` — отдельная схема не нужна (C2 fix)
- [ ] T047 [US7] (объединено с T015) — `parse_message()` уже возвращает ParsedMessage с batch_usages и batch_volume_liters для batch_usage событий; этот task закрыт T015
- [ ] T048 [US7] Создать `src/services/market_price.py`: функция `get_or_fetch_market_price(session) -> float` — если `market_price_updated_at` < сегодня или не установлена: вызвать `client.messages.create(tools=[{"name":"web_search","type":"web_search_20250305"}], ...)`; распарсить ответ через `client.messages.parse(output_format=MarketPriceResult, ...)` (M3+Принцип II fix); сохранить в user_settings; при ошибке парсинга или API — вернуть кешированное значение или 80.0
- [ ] T049 [US7] Создать `src/services/cost_calculator.py`: функция `calculate_batch_cost(session, parsed: ParsedMessage) -> dict` — для каждого ингредиента из parsed.batch_usages: найти в БД, конвертировать единицы через `unit_converter.convert_to_base_unit()` (M1 fix, общая утилита из T041), умножить на latest_price_per_unit; вернуть dict с itemized_costs, total_cost, cost_per_liter, cost_per_bottle, missing_ingredients
- [ ] T050 [US7] Реализовать `calculate_recommended_price(cost_per_bottle: float, market_price: float) -> float` в `src/services/cost_calculator.py`: `max(cost_per_bottle * 2, market_price * 0.9)`
- [ ] T051 [US7] Реализовать `save_batch(session, parsed, calc_result, market_price) -> Batch` в `src/models/batch.py`: создание Batch + BatchIngredientUsage записей; commit
- [ ] T052 [US7] Добавить обработку event_type=`batch_usage` в `src/handlers/messages.py` с conversation state (C1 fix): (1) проверить наличие `pending_batch_text` в user_settings — если есть И сообщение содержит только число → использовать pending_batch_text + volume → перейти к расчёту; (2) если batch_volume_liters=None → сохранить raw_text в `pending_batch_text` через set_setting() → уточнить у пользователя; (3) иначе → очистить pending_batch_text → calculate_batch_cost() → get_or_fetch_market_price() → calculate_recommended_price() → save_batch() → форматированный ответ
- [ ] T053 [US7] Создать `async def cost_handler(update, context)` в `src/handlers/commands.py`: показать последний Batch из БД; зарегистрировать `CommandHandler("cost", cost_handler)` в `src/bot.py`
- [ ] T054 [US7] Добавить миграцию `alembic/versions/0003_add_batches.py` (таблицы batches, batch_ingredient_usages)

**Checkpoint**: полный цикл: закупка → расход на партию → себестоимость → рыночная цена → рекомендованная цена.

---

## Phase 10: User Story 8 — Удаление записей по дате (P4)

**Цель**: `/delete 2026-05-04` → список событий → выбор номеров → удаление.

**Независимый тест**: записать 3 события → `/delete ДАТА` → удалить 1 → `/day ДАТА` показывает 2.

### Реализация US8

- [ ] T060 [P] [US8] Реализовать `get_events_for_date(session, date) -> list[Event]` в `src/services/analytics.py`; реализовать `delete_events_by_ids(session, ids: list[int])` в `src/models/event.py`
- [ ] T061 [US8] Создать `async def delete_handler(update, context)` в `src/handlers/commands.py`: парсит аргумент (дата или "all ДАТА"); выводит нумерованный список событий; сохраняет список в `pending_delete_ids` (user_settings) для следующего шага
- [ ] T062 [US8] Добавить в `src/handlers/messages.py` обработку ответа на delete: если pending_delete_ids в user_settings → парсить выбор пользователя (числа через запятую или "да"/"нет") → вызвать delete_events_by_ids() → очистить pending_delete_ids → подтвердить
- [ ] T063 [US8] Зарегистрировать `CommandHandler("delete", delete_handler)` в `src/bot.py`; добавить FR-026–028 в handlers/commands.py

**Checkpoint**: `/delete 2026-05-04` показывает список; выбор удаляет; `/day` отражает изменения.

---

## Phase N: Polish & Cross-Cutting Concerns

**Цель**: качество кода, dev-experience, базовые тесты.

- [ ] T055 [P] Создать `async def start_handler(update, context)` и `async def help_handler(update, context)` в `src/handlers/commands.py`; зарегистрировать в `src/bot.py`
- [ ] T056 [P] Написать интеграционный тест `tests/integration/test_parser.py`: 5 примеров из spec.md → parse_message() → проверить event_type и числа
- [ ] T057 [P] Написать интеграционный тест `tests/integration/test_analytics.py`: добавить события в тестовую БД → get_day_analytics() → проверить суммы
- [ ] T058 [P] Написать юнит-тест `tests/unit/test_calculations.py`: calculate_batch_cost() с известными данными, calculate_recommended_price() крайние случаи
- [ ] T059 Проверить quickstart.md: пройти шаги от начала до `/day` в реальном Telegram
- [ ] T064 [P] Реализовать `get_latest_batch_cost_per_bottle(session) -> Optional[float]` в `src/services/analytics.py` (M2 fix): запрос последнего Batch.cost_per_bottle_som; использовать в append_to_profit() для расчёта прибыли при записи в Sheets

---

## Dependencies & Execution Order

### Зависимости фаз

- **Phase 0** (Context7): выполнено ✅
- **Phase 1** (Setup): нет зависимостей — старт сразу
- **Phase 2** (Foundation): зависит от Phase 1 — БЛОКИРУЕТ все US
- **Phase 3** (US1): зависит от Phase 2
- **Phase 4** (US4): зависит от Phase 2
- **Phase 5** (US2): зависит от Phase 3 + Phase 4
- **Phase 6** (US3): зависит от Phase 5 (переиспользует analytics.py)
- **Phase 7** (US5): зависит от Phase 3 (интегрируется в messages.py)
- **Phase 8** (US6): зависит от Phase 2 (новые модели)
- **Phase 9** (US7): зависит от Phase 8 (использует ingredients)
- **Phase 10** (US8): зависит от Phase 2 (использует events)
- **Phase N** (Polish): зависит от всех предыдущих фаз

### Параллельные возможности

```bash
# Phase 1 — запустить вместе:
T002, T003, T004, T005, T006

# Phase 2 — запустить вместе после T007:
T008, T009

# Phase 3 — запустить вместе:
T014 (схема) → затем T015, T016 параллельно

# Phase 8 — запустить вместе:
T037, T038, T040 (независимые файлы)

# Phase N — все параллельно:
T055, T056, T057, T058
```

---

## Implementation Strategy

### MVP (только US1 — P1)

1. Phase 1: Setup
2. Phase 2: Foundation (обязательно)
3. Phase 3: US1 — запись событий
4. **СТОП и ПРОВЕРКА**: отправить 5 разных сообщений в Telegram, убедиться что все сохраняются
5. Деплой на Fly.io

### Полная реализация (все 7 US)

Последовательность: Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → N

Каждая фаза: реализовать → проверить → затем следующая.

---

## Notes

- `[P]` = задача не зависит от других незавершённых задач в той же фазе (разные файлы)
- `[USN]` = номер user story из spec.md
- Все пути относительно корня репозитория
- Тесты запускаются против реальной тестовой БД (не моки) — Принцип «Тестирование»
- Коммент в коде на русском, имена функций/переменных на английском — Принцип IV
