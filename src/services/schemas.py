"""Pydantic-схемы для LLM-вывода — без зависимости от anthropic."""

from datetime import date
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    PLACEMENT = "placement"
    SALE = "sale"
    EXPIRY_REMOVAL = "expiry_removal"
    MANUAL_COUNT = "manual_count"
    PRODUCTION_EXPENSE = "production_expense"
    INGREDIENT_PURCHASE = "ingredient_purchase"
    BATCH_USAGE = "batch_usage"
    UNKNOWN = "unknown"


class IngredientUsageItem(BaseModel):
    ingredient_name: str
    quantity: float
    unit: Literal["g", "kg", "ml", "l", "pcs"]


class MarketPriceResult(BaseModel):
    price_som: float = Field(description="Цена в сомах за бутылку 0.5л")


class ParsedMessage(BaseModel):
    event_type: EventType

    floor: Optional[int] = None
    quantity: Optional[int] = None
    bottle_volume_ml: Optional[int] = None
    product_name: Optional[str] = None
    amount_som: Optional[float] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    additional_events: Optional[list["ParsedMessage"]] = None

    ingredient_name: Optional[str] = None
    ingredient_quantity: Optional[float] = None
    ingredient_unit: Optional[Literal["g", "kg", "ml", "l", "pcs"]] = None
    ingredient_total_price_som: Optional[float] = None

    batch_usages: Optional[list[IngredientUsageItem]] = None
    batch_volume_liters: Optional[float] = None
