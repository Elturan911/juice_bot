from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_unit: Mapped[str] = mapped_column(String(5), nullable=False)
    latest_price_per_unit: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 6), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


def get_or_create_ingredient(session, name: str, base_unit: str) -> Ingredient:
    normalized = name.lower().strip()
    ingredient = session.query(Ingredient).filter_by(name=normalized).first()
    if not ingredient:
        ingredient = Ingredient(name=normalized, base_unit=base_unit)
        session.add(ingredient)
        session.commit()
    return ingredient
