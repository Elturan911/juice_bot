"""Обработчики для клиентов (не-администраторов)."""

import logging
import os
from datetime import date, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.keyboards import (
    BTN_C_FLOOR_2,
    BTN_C_FLOOR_3,
    CUSTOMER_KEYBOARD,
    order_tomorrow_keyboard,
)
from src.models.base import Session
from src.models.tomorrow_order import create_tomorrow_order, get_order_summary
from src.services.stock import format_floor_product_stock, get_floor_product_stock, get_floor_total

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))


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
        stock = get_floor_product_stock(session)
    remaining = get_floor_total(stock, floor)

    if remaining <= 0:
        await query.edit_message_text(
            f"К сожалению, на {floor}-м этаже закончился сок.\n"
            "Можно проверить другой этаж или заказать бутылку на завтра.",
            reply_markup=order_tomorrow_keyboard(floor),
        )
        return

    await query.edit_message_text(format_floor_product_stock(stock, floor))


async def handle_order_tomorrow_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    query = update.callback_query
    await query.answer()

    try:
        floor = int((query.data or "").split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка заказа.")
        return

    order_date = date.today() + timedelta(days=1)
    customer_chat_id = query.from_user.id

    with Session() as session:
        create_tomorrow_order(session, customer_chat_id, floor, order_date)
        summary = get_order_summary(session, order_date)

    await query.edit_message_text(
        f"✅ Заказал 1 бутылку на завтра на {floor}-й этаж.\n"
        "Спасибо! Завтра постараемся привезти свежий компот."
    )

    if ADMIN_CHAT_ID:
        await _notify_admin_about_tomorrow_order(context, floor, order_date, summary)


async def _send_floor_stock(update: Update, floor: int) -> None:
    with Session() as session:
        stock = get_floor_product_stock(session)
    remaining = get_floor_total(stock, floor)

    if remaining <= 0:
        await update.message.reply_text(
            f"К сожалению, на {floor}-м этаже закончился сок.\n"
            "Можно проверить другой этаж или заказать бутылку на завтра.",
            reply_markup=order_tomorrow_keyboard(floor),
        )
        return

    await update.message.reply_text(
        format_floor_product_stock(stock, floor),
        reply_markup=CUSTOMER_KEYBOARD,
    )


async def _send_welcome(update: Update) -> None:
    await update.message.reply_text(
        "Привет! 🍹 Выбери этаж, чтобы посмотреть сколько компота осталось.",
        reply_markup=CUSTOMER_KEYBOARD,
    )


async def _notify_admin_about_tomorrow_order(
    context: ContextTypes.DEFAULT_TYPE,
    floor: int,
    order_date: date,
    summary: dict[int, int],
) -> None:
    lines = [
        "📦 Новый заказ на завтра!",
        f"🏢 Этаж: {floor}",
        "",
        f"Сводка на {order_date.strftime('%d.%m.%Y')}:",
    ]
    total = 0
    for floor_num in (2, 3):
        count = summary.get(floor_num, 0)
        lines.append(f"🏢 {floor_num}-й этаж: {count} бутылок")
        total += count
    lines.append(f"\nВсего приготовить под заказы: {total} бутылок")

    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text="\n".join(lines))
    except Exception as e:
        logger.error(f"admin tomorrow order notify error: {e}")
