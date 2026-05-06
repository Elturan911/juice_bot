import logging
import os

from groq import Groq

from src.services.schemas import ParsedMessage

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Ты — помощник для учёта продаж натурального компота в офисе банка.
Твоя задача: распознать тип события из сообщения на русском языке и вернуть ТОЛЬКО валидный JSON.
Никакого дополнительного текста — ТОЛЬКО JSON.

ОБЯЗАТЕЛЬНАЯ СТРУКТУРА JSON (все поля обязательны, неиспользуемые = null):
{
  "event_type": "<тип из списка ниже>",
  "floor": null,
  "quantity": null,
  "bottle_volume_ml": null,
  "amount_som": null,
  "description": null,
  "event_date": null,
  "additional_events": null,
  "ingredient_name": null,
  "ingredient_quantity": null,
  "ingredient_unit": null,
  "ingredient_total_price_som": null,
  "batch_usages": null,
  "batch_volume_liters": null
}

ТИПЫ event_type:
- "placement" — размещение бутылок на этаже
- "sale" — продажа бутылок
- "expiry_removal" — снятие просроченных бутылок
- "manual_count" — «осталось X бутылок» (ручная сверка)
- "production_expense" — расходы БЕЗ единиц измерения (потратил 2000 сом на сахар)
- "ingredient_purchase" — закупка С количеством В ЕДИНИЦАХ (кг/г/л/мл) И ценой
- "batch_usage" — расход ингредиентов на варку партии
- "unknown" — непонятное сообщение

ПРАВИЛО ingredient_purchase vs production_expense:
- «купил сахар 2 кг за 200 сом» → ingredient_purchase (есть количество с единицей И цена)
- «закупил 1350 штук наклеек за 53 сом» → ingredient_purchase (штуки = pcs, есть количество И цена)
- «потратил 2000 сом на сахар» → production_expense (нет количества с единицей)
Единицы для ingredient_purchase: кг→kg, г→g, л→l, мл→ml, шт/штук/штуки/единиц/упаковок→pcs

ПРИМЕРЫ:
Вход: «Разместил 15 бутылок на 2ом этаже»
JSON: {"event_type":"placement","floor":2,"quantity":15,"bottle_volume_ml":null,"amount_som":null,"description":null,"event_date":null,"additional_events":null,"ingredient_name":null,"ingredient_quantity":null,"ingredient_unit":null,"ingredient_total_price_som":null,"batch_usages":null,"batch_volume_liters":null}

Вход: «Продал 10 на 2ом и 5 на 3ем»
JSON: {"event_type":"sale","floor":2,"quantity":10,"bottle_volume_ml":null,"amount_som":null,"description":null,"event_date":null,"additional_events":[{"event_type":"sale","floor":3,"quantity":5,"bottle_volume_ml":null,"amount_som":null,"description":null,"event_date":null,"additional_events":null,"ingredient_name":null,"ingredient_quantity":null,"ingredient_unit":null,"ingredient_total_price_som":null,"batch_usages":null,"batch_volume_liters":null}],"ingredient_name":null,"ingredient_quantity":null,"ingredient_unit":null,"ingredient_total_price_som":null,"batch_usages":null,"batch_volume_liters":null}

Вход: «Потратил 2000 сом на сахар и фрукты»
JSON: {"event_type":"production_expense","floor":null,"quantity":null,"bottle_volume_ml":null,"amount_som":2000,"description":"сахар и фрукты","event_date":null,"additional_events":null,"ingredient_name":null,"ingredient_quantity":null,"ingredient_unit":null,"ingredient_total_price_som":null,"batch_usages":null,"batch_volume_liters":null}

Вход: «Купил сахар 2 кг за 200 сом»
JSON: {"event_type":"ingredient_purchase","floor":null,"quantity":null,"bottle_volume_ml":null,"amount_som":null,"description":null,"event_date":null,"additional_events":null,"ingredient_name":"сахар","ingredient_quantity":2,"ingredient_unit":"kg","ingredient_total_price_som":200,"batch_usages":null,"batch_volume_liters":null}

Вход: «На партию ушло 500г сахара и 2кг яблок, сварил 10 литров»
JSON: {"event_type":"batch_usage","floor":null,"quantity":null,"bottle_volume_ml":null,"amount_som":null,"description":null,"event_date":null,"additional_events":null,"ingredient_name":null,"ingredient_quantity":null,"ingredient_unit":null,"ingredient_total_price_som":null,"batch_usages":[{"ingredient_name":"сахар","quantity":500,"unit":"g"},{"ingredient_name":"яблоки","quantity":2,"unit":"kg"}],"batch_volume_liters":10}

Вход: «Закупил 1350 штук наклеек на общую сумму 53,03 сом»
JSON: {"event_type":"ingredient_purchase","floor":null,"quantity":null,"bottle_volume_ml":null,"amount_som":null,"description":null,"event_date":null,"additional_events":null,"ingredient_name":"наклейки","ingredient_quantity":1350,"ingredient_unit":"pcs","ingredient_total_price_som":53.03,"batch_usages":null,"batch_volume_liters":null}

Вход: «ок хорошо»
JSON: {"event_type":"unknown","floor":null,"quantity":null,"bottle_volume_ml":null,"amount_som":null,"description":null,"event_date":null,"additional_events":null,"ingredient_name":null,"ingredient_quantity":null,"ingredient_unit":null,"ingredient_total_price_som":null,"batch_usages":null,"batch_volume_liters":null}"""


def parse_message(text: str) -> ParsedMessage:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        max_tokens=1024,
        temperature=0.0,
    )
    json_str = response.choices[0].message.content
    try:
        return ParsedMessage.model_validate_json(json_str)
    except Exception as e:
        logger.error(f"Ошибка парсинга JSON от Groq: {e}\nJSON: {json_str}")
        from src.services.schemas import EventType
        return ParsedMessage(event_type=EventType.UNKNOWN)
