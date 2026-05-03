from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CustomerPurchase(Base):
    __tablename__ = "customer_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_som: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="text")
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
