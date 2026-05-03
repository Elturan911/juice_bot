"""Обработчики для клиентов (не-администраторов)."""
import base64
import io
import json
import logging
import os
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from src.handlers.keyboards import CUSTOMER_KEYBOARD, FLOOR_KEYBOARD, BTN_C_BUY, BTN_C_STOCK
from src.models.base import Session
from src.models.customer_purchase import CustomerPurchase
from src.models.settings import delete_setting, get_setting, set_setting
from src.services.stock import format_stock_report, get_floor_stock

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))


async def handle_customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id

    try:
        if text == BTN_C_STOCK:
            await _send_stock(update)
            return

        if text == BTN_C_BUY:
            await update.message.reply_text(
                "Пришли фото чека 📸 или напиши что купил:\n"
                "Например: «2 бутылки компота»",
                reply_markup=CUSTOMER_KEYBOARD,
            )
            with Session() as session:
                set_setting(session, f"c_state_{chat_id}", "awaiting_info")
            return

        # Проверяем состояние
        with Session() as session:
            state = get_setting(session, f"c_state_{chat_id}")

        if state == "awaiting_info":
            await _handle_purchase_info(update, context, text)
            return

        # Любое другое сообщение — показываем приветствие
        await _send_welcome(update)

    except Exception as e:
        logger.error(f"customer handler error: {e}", exc_info=True)
        await update.message.reply_text("😔 Что-то пошло не так. Попробуй ещё раз.")


async def handle_customer_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    try:
        await update.message.reply_text("📸 Читаю чек...")

        # Скачиваем фото и конвертируем в base64
        photo = update.message.photo[-1]  # самое высокое разрешение
        tg_file = await context.bot.get_file(photo.file_id)
        buf = io.BytesIO()
        await tg_file.download_to_memory(buf)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode()

        # Groq Vision
        description = await _read_receipt_with_vision(img_b64)

        if not description:
            await update.message.reply_text(
                "❌ Не смог прочитать чек. Напиши текстом что купил:\n"
                "Например: «2 бутылки компота»"
            )
            with Session() as session:
                set_setting(session, f"c_state_{chat_id}", "awaiting_info")
            return

        await update.message.reply_text(f"✅ Распознал: «{description}»")
        await _ask_floor(update, context, description, source="photo")

    except Exception as e:
        logger.error(f"customer photo error: {e}", exc_info=True)
        await update.message.reply_text("😔 Ошибка при обработке фото.")


async def _read_receipt_with_vision(img_b64: str) -> str | None:
    from groq import Groq
    try:
        client = Groq(api_key=os.environ["GROQ_API_KEY"])
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Это чек из офиса. Напиши кратко что куплено: "
                            "название товара и количество. "
                            "Если это компот — укажи сколько бутылок. "
                            "Ответь одной строкой по-русски."
                        ),
                    },
                ],
            }],
            max_tokens=128,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"vision error: {e}")
        return None


async def _handle_purchase_info(update: Update, context, text: str) -> None:
    chat_id = update.effective_chat.id
    with Session() as session:
        delete_setting(session, f"c_state_{chat_id}")
    await _ask_floor(update, context, text, source="text")


async def _ask_floor(update: Update, context, description: str, source: str) -> None:
    chat_id = update.effective_chat.id
    pending = json.dumps({"desc": description, "source": source})
    with Session() as session:
        set_setting(session, f"c_floor_{chat_id}", pending)

    await update.message.reply_text(
        "На каком этаже брал компот?",
        reply_markup=FLOOR_KEYBOARD,
    )


async def handle_floor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = query.from_user.id
    data = query.data  # "floor:2" или "floor:3"

    try:
        floor = int(data.split(":")[1])
    except (IndexError, ValueError):
        await query.edit_message_text("❌ Ошибка выбора этажа.")
        return

    with Session() as session:
        pending_str = get_setting(session, f"c_floor_{chat_id}")
        delete_setting(session, f"c_floor_{chat_id}")

        if not pending_str:
            await query.edit_message_text("❌ Сессия устарела. Начни заново.")
            return

        pending = json.loads(pending_str)
        description = pending["desc"]
        source = pending["source"]

        # Сохраняем покупку клиента
        purchase = CustomerPurchase(
            customer_chat_id=chat_id,
            floor=floor,
            description=description,
            source=source,
            purchase_date=date.today(),
        )
        session.add(purchase)
        session.commit()

        # Остаток на этаже
        stock = get_floor_stock(session)
        remaining = stock.get(floor, "?")

    await query.edit_message_text(
        f"✅ Спасибо! Записал покупку на {floor}-м этаже.\n"
        f"🍾 На {floor}-м этаже сейчас примерно {remaining} бутылок."
    )

    # Уведомляем администратора
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=(
                    f"🛒 Новая покупка!\n"
                    f"🏢 Этаж: {floor}\n"
                    f"📝 {description}\n"
                    f"📦 Остаток на этаже: ~{remaining} шт"
                ),
            )
        except Exception as e:
            logger.error(f"admin notify error: {e}")


async def _send_stock(update: Update) -> None:
    with Session() as session:
        stock = get_floor_stock(session)
    text = format_stock_report(stock)
    await update.message.reply_text(text, reply_markup=CUSTOMER_KEYBOARD)


async def _send_welcome(update: Update) -> None:
    await update.message.reply_text(
        "Привет! 🍹 Здесь можно узнать остатки компота или сообщить о покупке.",
        reply_markup=CUSTOMER_KEYBOARD,
    )
