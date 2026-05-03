"""Интеграционные тесты LLM-парсера (требуется ANTHROPIC_API_KEY)."""
import os

import pytest

from src.services.parser import parse_message
from src.services.schemas import EventType


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY не установлен"
)
def test_parse_placement():
    result = parse_message("Разместил 15 бутылок на 2ом этаже")
    assert result.event_type == EventType.PLACEMENT
    assert result.floor == 2
    assert result.quantity == 15


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY не установлен"
)
def test_parse_sale():
    result = parse_message("Продал 10 бутылок на 2ом этаже")
    assert result.event_type == EventType.SALE
    assert result.floor == 2
    assert result.quantity == 10


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY не установлен"
)
def test_parse_expiry():
    result = parse_message("Забрал просрочку 5 бутылок с 3го этажа")
    assert result.event_type == EventType.EXPIRY_REMOVAL
    assert result.quantity == 5


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY не установлен"
)
def test_parse_ingredient_purchase():
    result = parse_message("Купил сахар 2 кг за 200 сом")
    assert result.event_type == EventType.INGREDIENT_PURCHASE
    assert result.ingredient_name is not None
    assert "сахар" in result.ingredient_name.lower()
    assert result.ingredient_quantity == 2.0
    assert result.ingredient_total_price_som == 200.0


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY не установлен"
)
def test_parse_production_expense_no_units():
    result = parse_message("Потратил 2000 сом на сахар и фрукты")
    assert result.event_type == EventType.PRODUCTION_EXPENSE
    assert float(result.amount_som) == 2000.0


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY не установлен"
)
def test_parse_unknown():
    result = parse_message("ок хорошо")
    assert result.event_type == EventType.UNKNOWN
