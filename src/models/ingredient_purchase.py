from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class IngredientPurchase(Base):
    __tablename__ = "ingredient_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ingredients.id"), nullable=False
    )
    quantity_base: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    total_price_som: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_per_unit: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    ingredient = relationship("Ingredient")
