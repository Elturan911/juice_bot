"""Интеграционные тесты аналитики (требуется реальная тестовая БД)."""
import os
from datetime import date

import pytest

from src.models.base import Base, Session, engine
from src.models.event import Event, save_events
from src.models.settings import set_setting
from src.services.analytics import get_day_analytics, get_week_analytics


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


def test_day_analytics_no_events():
    with Session() as session:
        result = get_day_analytics(session, date(2026, 1, 1))
    assert result == {}


def test_day_analytics_sales():
    target = date(2026, 5, 4)
    with Session() as session:
        set_setting(session, "bottle_price", "100")
        save_events(session, "sale", 2, 10, None, None, None, "продал", target)
        save_events(session, "sale", 3, 5, None, None, None, "продал", target)
        save_events(session, "production_expense", None, None, None, 500.0,
                    "расходы", "потратил", target)

        result = get_day_analytics(session, target)

    assert result["sold"] == 15
    assert result["revenue"] == 1500.0
    assert result["expenses"] == 500.0
    assert result["profit"] == 1000.0
    assert result["sales_by_floor"][2] == 10
    assert result["sales_by_floor"][3] == 5


def test_week_analytics_aggregates():
    with Session() as session:
        set_setting(session, "bottle_price", "100")
        # 3 дня подряд
        for i in range(3):
            d = date(2026, 5, 4 + i)
            save_events(session, "sale", 2, 5, None, None, None, "продал", d)

        result = get_week_analytics(session, date(2026, 5, 4))

    assert result["sold"] == 15
    assert result["revenue"] == 1500.0
