from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, Index, func, select
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class TomorrowOrder(Base):
    __tablename__ = "tomorrow_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_tomorrow_orders_order_date", "order_date"),
        Index("ix_tomorrow_orders_customer", "customer_chat_id"),
    )


def create_tomorrow_order(
    session,
    customer_chat_id: int,
    floor: int,
    order_date: date,
) -> TomorrowOrder:
    order = TomorrowOrder(
        customer_chat_id=customer_chat_id,
        floor=floor,
        quantity=1,
        order_date=order_date,
    )
    session.add(order)
    session.commit()
    return order


def get_order_summary(session, order_date: date) -> dict[int, int]:
    orders = session.scalars(
        select(TomorrowOrder).where(TomorrowOrder.order_date == order_date)
    ).all()

    summary: dict[int, int] = {}
    for order in orders:
        summary[order.floor] = summary.get(order.floor, 0) + order.quantity
    return dict(sorted(summary.items()))
