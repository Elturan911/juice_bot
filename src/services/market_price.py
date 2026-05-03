import logging
from datetime import date

from src.models.settings import get_setting, set_setting

logger = logging.getLogger(__name__)

DEFAULT_PRICE = 80.0


def get_or_fetch_market_price(session) -> float:
    """Возвращает текущую рыночную цену компота в Бишкеке (сом/0.5л).
    Берётся из user_settings (устанавливается командой /setmarketprice).
    По умолчанию: 80 сом.
    """
    cached = get_setting(session, "market_price_som")
    return float(cached) if cached else DEFAULT_PRICE


def set_market_price(session, price: float) -> None:
    set_setting(session, "market_price_som", str(price))
    set_setting(session, "market_price_updated_at", date.today().isoformat())
    logger.info(f"Рыночная цена обновлена вручную: {price} сом")
