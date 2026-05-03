from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import mapped_column

from .base import Base


class UserSetting(Base):
    __tablename__ = "user_settings"

    id: int = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: str = mapped_column(String(50), unique=True, nullable=False)
    value: str = mapped_column(Text, nullable=False)
    updated_at: datetime = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


def get_setting(session, key: str) -> str | None:
    setting = session.query(UserSetting).filter_by(key=key).first()
    return setting.value if setting else None


def set_setting(session, key: str, value: str) -> None:
    setting = session.query(UserSetting).filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = UserSetting(key=key, value=value)
        session.add(setting)
    session.commit()


def delete_setting(session, key: str) -> None:
    setting = session.query(UserSetting).filter_by(key=key).first()
    if setting:
        session.delete(setting)
        session.commit()
