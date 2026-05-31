"""Обработчики для клиентов (не-администраторов)."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.keyboards import (
    BTN_C_FLOOR_2,
    BTN_C_FLOOR_3,
    CUSTOMER_KEYBOARD,
)
from src.models.base import Session
from src.services.stock import get_floor_stock

logger = logging.getLogger(__name__)


async def handle_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()

    try:
        if text == BTN_C_FLOOR_2:
            await _send_floor_stock(update, 2)
            return

        if text == BTN_C_FLOOR_3:
            await _send_floor_stock(update, 3)
            return

        await _send_welcome(update)

    except Exception as e:
        logger.error(f"customer handler error: {e}", exc_info=True)
        await update.message.reply_text("😔 Что-то пошло не так. Попробуй ещё раз.")


async def handle_customer_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Пока клиентам доступен только просмотр остатков компота по этажам.",
        reply_markup=CUSTOMER_KEYBOARD,
    )


async def handle_floor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    try:
        floor = int((query.data or "").split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка выбора этажа.")
        return

    with Session() as session:
        stock = get_floor_stock(session)
    remaining = stock.get(floor, 0)

    await query.edit_message_text(
        f"🍾 На {floor}-м этаже сейчас примерно {remaining} бутылок."
    )


async def _send_floor_stock(update: Update, floor: int) -> None:
    with Session() as session:
        stock = get_floor_stock(session)
    remaining = stock.get(floor, 0)

    await update.message.reply_text(
        f"🍾 На {floor}-м этаже сейчас примерно {remaining} бутылок.",
        reply_markup=CUSTOMER_KEYBOARD,
    )


async def _send_welcome(update: Update) -> None:
    await update.message.reply_text(
        "Привет! 🍹 Выбери этаж, чтобы посмотреть сколько компота осталось.",
        reply_markup=CUSTOMER_KEYBOARD,
    )
