import logging
import os
from datetime import date

import anthropic

from src.models.settings import get_setting, set_setting
from src.services.schemas import MarketPriceResult

logger = logging.getLogger(__name__)

MODEL_SEARCH = "claude-sonnet-4-6"
DEFAULT_PRICE = 80.0

SEARCH_PROMPT = (
    "Найди текущую среднюю рыночную цену натурального домашнего компота "
    "в Бишкеке, Кыргызстан за бутылку объёмом 0.5 литра. "
    "Используй веб-поиск для актуальных данных."
)

EXTRACT_PROMPT_TEMPLATE = (
    "На основе следующей информации о ценах компота в Бишкеке, "
    "определи среднюю цену за бутылку 0.5 литра в кыргызских сомах. "
    "Если точных данных нет, оцени исходя из доступной информации.\n\n{context}"
)


def get_or_fetch_market_price(session) -> float:
    today = date.today().isoformat()
    updated_at = get_setting(session, "market_price_updated_at")

    if updated_at == today:
        cached = get_setting(session, "market_price_som")
        if cached:
            return float(cached)

    try:
        price = _fetch_from_web()
        set_setting(session, "market_price_som", str(price))
        set_setting(session, "market_price_updated_at", today)
        logger.info(f"Рыночная цена обновлена: {price} сом")
        return price
    except Exception as e:
        logger.warning(f"Не удалось получить рыночную цену: {e}")
        cached = get_setting(session, "market_price_som")
        return float(cached) if cached else DEFAULT_PRICE


def _fetch_from_web() -> float:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Шаг 1: поиск через web_search
    search_response = client.messages.create(
        model=MODEL_SEARCH,
        max_tokens=512,
        messages=[{"role": "user", "content": SEARCH_PROMPT}],
        tools=[{"name": "web_search", "type": "web_search_20250305"}],
    )

    search_text = " ".join(
        block.text for block in search_response.content if hasattr(block, "text")
    )

    # Шаг 2: структурированное извлечение числа через Pydantic (Принцип II)
    extract_result = client.messages.parse(
        model=MODEL_SEARCH,
        max_tokens=64,
        messages=[{
            "role": "user",
            "content": EXTRACT_PROMPT_TEMPLATE.format(context=search_text or "нет данных"),
        }],
        output_format=MarketPriceResult,
    )
    price = extract_result.parsed_output.price_som
    if price <= 0:
        raise ValueError(f"Некорректная цена: {price}")
    return price
