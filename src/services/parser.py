import os

import anthropic

from src.services.schemas import EventType, IngredientUsageItem, MarketPriceResult, ParsedMessage

MODEL_PARSE = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Ты — помощник для учёта продаж компота в офисе банка.
Твоя задача: распознать тип события из сообщения пользователя на русском языке и извлечь данные.

ТИПЫ СОБЫТИЙ:
- placement: размещение бутылок на этаже
- sale: продажа бутылок
- expiry_removal: снятие просроченных бутылок
- manual_count: ручная сверка остатка («осталось X бутылок»)
- production_expense: общие расходы БЕЗ указания количества ингредиента
- ingredient_purchase: закупка ингредиента — ТОЛЬКО если указаны И количество в единицах И цена
- batch_usage: расход ингредиентов на партию компота
- unknown: сообщение не относится ни к одному типу

ПРАВИЛО ingredient_purchase vs production_expense:
- «купил сахар 2 кг за 200 сом» → ingredient_purchase
- «потратил 2000 сом на сахар» → production_expense (нет единиц измерения)

ПРИМЕРЫ:
1. «Разместил 15 бутылок на 2ом этаже» → placement, floor=2, quantity=15
2. «Продал 10 на 2ом и 5 на 3ем» → sale floor=2 qty=10 + additional_events: sale floor=3 qty=5
3. «Забрал просрочку 5 бутылок с 3го этажа» → expiry_removal, floor=3, quantity=5
4. «Потратил 2000 сом на сахар и фрукты» → production_expense, amount_som=2000
5. «Купил сахар 2 кг за 200 сом» → ingredient_purchase, name=сахар, qty=2, unit=kg, price=200
6. «На партию ушло 500г сахара и 2кг яблок, сварил 10 л» → batch_usage

Если дата не указана — оставь event_date=null."""


def parse_message(text: str) -> ParsedMessage:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    result = client.messages.parse(
        model=MODEL_PARSE,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        output_format=ParsedMessage,
    )
    return result.parsed_output
