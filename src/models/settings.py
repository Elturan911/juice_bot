from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


def get_setting(session, key: str) -> str | None:
    s = session.query(UserSetting).filter_by(key=key).first()
    return s.value if s else None


def set_setting(session, key: str, value: str) -> None:
    s = session.query(UserSetting).filter_by(key=key).first()
    if s:
        s.value = value
    else:
        s = UserSetting(key=key, value=value)
        session.add(s)
    session.commit()


def delete_setting(session, key: str) -> None:
    s = session.query(UserSetting).filter_by(key=key).first()
    if s:
        session.delete(s)
        session.commit()


def get_registered_customer_chat_ids(session) -> list[int]:
    settings = (
        session.query(UserSetting)
        .filter(UserSetting.key.like("c_registered_%"))
        .all()
    )

    chat_ids: list[int] = []
    for setting in settings:
        raw_chat_id = setting.key.removeprefix("c_registered_")
        try:
            chat_ids.append(int(raw_chat_id))
        except ValueError:
            continue
    return chat_ids
