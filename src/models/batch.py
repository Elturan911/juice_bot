from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_date: Mapped[date] = mapped_column(Date, nullable=False)
    volume_liters: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    total_ingredient_cost_som: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    cost_per_liter_som: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    cost_per_bottle_som: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    recommended_price_som: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    market_price_used_som: Mapped[Optional[float]] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


def save_batch(session, batch_date, volume_liters, total_cost, cost_per_liter,
               cost_per_bottle, recommended_price, market_price, raw_text) -> Batch:
    batch = Batch(
        batch_date=batch_date, volume_liters=volume_liters,
        total_ingredient_cost_som=total_cost, cost_per_liter_som=cost_per_liter,
        cost_per_bottle_som=cost_per_bottle, recommended_price_som=recommended_price,
        market_price_used_som=market_price, raw_text=raw_text,
    )
    session.add(batch)
    session.commit()
    return batch
