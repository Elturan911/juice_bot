from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bottle_volume_ml: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amount_som: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_events_event_date", "event_date"),)


def save_events(session, event_type: str, floor, quantity, bottle_volume_ml,
                amount_som, description, raw_text: str, event_date) -> list[Event]:
    from datetime import date as date_cls
    target_date = event_date or date_cls.today()
    event = Event(
        event_type=event_type, floor=floor, quantity=quantity,
        bottle_volume_ml=bottle_volume_ml, amount_som=amount_som,
        description=description, raw_text=raw_text, event_date=target_date,
    )
    session.add(event)
    session.commit()
    return [event]


def delete_events_by_ids(session, ids: list[int]) -> int:
    deleted = 0
    for eid in ids:
        ev = session.get(Event, eid)
        if ev:
            session.delete(ev)
            deleted += 1
    session.commit()
    return deleted
