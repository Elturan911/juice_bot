"""Юнит-тесты для расчётов себестоимости и рекомендованной цены."""
from src.services.cost_calculator import calculate_recommended_price  # noqa: E402
from src.services.unit_converter import convert_to_base_unit, get_base_unit


def test_convert_kg_to_g():
    assert convert_to_base_unit(2.0, "kg") == 2000.0


def test_convert_l_to_ml():
    assert convert_to_base_unit(1.5, "l") == 1500.0


def test_convert_g_unchanged():
    assert convert_to_base_unit(500.0, "g") == 500.0


def test_get_base_unit_kg():
    assert get_base_unit("kg") == "g"


def test_get_base_unit_l():
    assert get_base_unit("l") == "ml"


def test_recommended_price_cost_dominant():
    # Когда себестоимость × 2 > рыночная × 0.9
    cost = 100.0
    market = 150.0
    result = calculate_recommended_price(cost, market)
    assert result == max(cost * 2, market * 0.9)
    assert result == 200.0


def test_recommended_price_market_dominant():
    # Когда рыночная × 0.9 > себестоимость × 2
    cost = 10.0
    market = 150.0
    result = calculate_recommended_price(cost, market)
    assert result == max(cost * 2, market * 0.9)
    assert result == 135.0


def test_recommended_price_default_market():
    # С дефолтной рыночной ценой 80 сом
    cost = 12.5
    market = 80.0
    result = calculate_recommended_price(cost, market)
    assert result == max(12.5 * 2, 80.0 * 0.9)
    assert result == 72.0
