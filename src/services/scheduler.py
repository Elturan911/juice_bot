import logging
from datetime import date, time

import pytz
from telegram.ext import ContextTypes

from src.models.base import Session
from src.models.settings import get_setting, set_setting
from src.services.analytics import format_period_report, get_day_analytics

logger = logging.getLogger(__name__)

BISHKEK_TZ = pytz.timezone("Asia/Bishkek")
DAILY_REPORT_TIME = time(22, 0, 0, tzinfo=BISHKEK_TZ)


async def daily_report_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    with Session() as session:
        chat_id = get_setting(session, "chat_id")
        if not chat_id:
            logger.warning("daily_report: chat_id не найден — /start не был вызван")
            return

        today = date.today()
        analytics = get_day_analytics(session, today)

    if analytics:
        label = f"📅 Итоги дня — {today.strftime('%d.%m.%Y')}"
        text = format_period_report(analytics, label)
        text += "\n\n_Автоотчёт в 22:00_ 🕙"
    else:
        text = (
            f"📭 {today.strftime('%d.%m.%Y')} — записей нет.\n"
            "Не забудь записать продажи, если были!"
        )

    try:
        await context.bot.send_message(chat_id=int(chat_id), text=text)
    except Exception as e:
        logger.error(f"daily_report: не удалось отправить: {e}")
