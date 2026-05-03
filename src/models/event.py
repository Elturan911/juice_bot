from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, func
from sqlalchemy.orm import mapped_column

from .base import Base


class Event(Base):
    __tablename__ = "events"

    id: int = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: str = mapped_column(String(30), nullable=False)
    floor: int | None = mapped_column(Integer, nullable=True)
    quantity: int | None = mapped_column(Integer, nullable=True)
    bottle_volume_ml: int | None = mapped_column(Integer, nullable=True)
    amount_som: float | None = mapped_column(Numeric(10, 2), nullable=True)
    description: str | None = mapped_column(Text, nullable=True)
    raw_text: str = mapped_column(Text, nullable=False)
    event_date: date = mapped_column(Date, nullable=False)
    created_at: datetime = mapped_column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (Index("ix_events_event_date", "event_date"),)


def save_events(session, event_type: str, floor: int | None, quantity: int | None,
                bottle_volume_ml: int | None, amount_som: float | None,
                description: str | None, raw_text: str,
                event_date: date | None) -> list["Event"]:
    from datetime import date as date_cls
    target_date = event_date or date_cls.today()

    event = Event(
        event_type=event_type,
        floor=floor,
        quantity=quantity,
        bottle_volume_ml=bottle_volume_ml,
        amount_som=amount_som,
        description=description,
        raw_text=raw_text,
        event_date=target_date,
    )
    session.add(event)
    session.commit()
    return [event]


def delete_events_by_ids(session, ids: list[int]) -> int:
    deleted = 0
    for event_id in ids:
        event = session.get(Event, event_id)
        if event:
            session.delete(event)
            deleted += 1
    session.commit()
    return deleted
