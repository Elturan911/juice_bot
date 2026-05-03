from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, Text, func
from sqlalchemy.orm import mapped_column

from .base import Base


class Batch(Base):
    __tablename__ = "batches"

    id: int = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_date: date = mapped_column(Date, nullable=False)
    volume_liters: float = mapped_column(Numeric(6, 2), nullable=False)
    total_ingredient_cost_som: float | None = mapped_column(Numeric(10, 2), nullable=True)
    cost_per_liter_som: float | None = mapped_column(Numeric(10, 2), nullable=True)
    cost_per_bottle_som: float | None = mapped_column(Numeric(10, 2), nullable=True)
    recommended_price_som: float | None = mapped_column(Numeric(10, 2), nullable=True)
    market_price_used_som: float | None = mapped_column(Numeric(10, 2), nullable=True)
    raw_text: str = mapped_column(Text, nullable=False)
    created_at: datetime = mapped_column(DateTime, default=func.now(), nullable=False)


def save_batch(session, batch_date: date, volume_liters: float,
               total_cost: float, cost_per_liter: float, cost_per_bottle: float,
               recommended_price: float, market_price: float,
               raw_text: str) -> "Batch":
    batch = Batch(
        batch_date=batch_date,
        volume_liters=volume_liters,
        total_ingredient_cost_som=total_cost,
        cost_per_liter_som=cost_per_liter,
        cost_per_bottle_som=cost_per_bottle,
        recommended_price_som=recommended_price,
        market_price_used_som=market_price,
        raw_text=raw_text,
    )
    session.add(batch)
    session.commit()
    return batch
