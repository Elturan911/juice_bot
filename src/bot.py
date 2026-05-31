import logging
import os

from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    JobQueue,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))


def _is_admin(update) -> bool:
    return update.effective_chat.id == ADMIN_CHAT_ID


def _admin_only(handler):
    async def wrapped(update, context):
        if _is_admin(update):
            await handler(update, context)
            return

        from src.handlers.keyboards import CUSTOMER_KEYBOARD

        await update.message.reply_text(
            "Здесь можно только посмотреть остатки компота по этажам.",
            reply_markup=CUSTOMER_KEYBOARD,
        )

    return wrapped


def main() -> None:
    from src.handlers.commands import (
        breakeven_handler,
        cost_handler,
        day_handler,
        delete_handler,
        help_handler,
        month_handler,
        setmarketprice_handler,
        setprice_handler,
        sheet_handler,
        start_handler,
        stock_handler,
        tomorrow_orders_handler,
        week_handler,
    )
    from src.handlers.customer import (
        handle_customer_message,
        handle_customer_photo,
        handle_floor_callback,
        handle_order_tomorrow_callback,
    )
    from src.handlers.messages import handle_message, handle_voice
    from src.services.scheduler import DAILY_REPORT_TIME, daily_report_job

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).job_queue(JobQueue()).build()

    # ── Общие команды ─────────────────────────────────────────────────────
    async def smart_start(update, context):
        if _is_admin(update):
            await start_handler(update, context)
        else:
            from src.handlers.keyboards import CUSTOMER_KEYBOARD
            from src.models.base import Session
            from src.models.settings import set_setting
            with Session() as session:
                set_setting(session, f"c_registered_{update.effective_chat.id}", "1")
            await update.message.reply_text(
                "Привет! 🍹 Выбери этаж, чтобы посмотреть сколько компота осталось.",
                reply_markup=CUSTOMER_KEYBOARD,
            )

    app.add_handler(CommandHandler("start", smart_start))

    # ── Команды администратора ────────────────────────────────────────────
    app.add_handler(CommandHandler("help", _admin_only(help_handler)))
    app.add_handler(CommandHandler("setprice", _admin_only(setprice_handler)))
    app.add_handler(CommandHandler("setmarketprice", _admin_only(setmarketprice_handler)))
    app.add_handler(CommandHandler("day", _admin_only(day_handler)))
    app.add_handler(CommandHandler("week", _admin_only(week_handler)))
    app.add_handler(CommandHandler("month", _admin_only(month_handler)))
    app.add_handler(CommandHandler("cost", _admin_only(cost_handler)))
    app.add_handler(CommandHandler("sheet", _admin_only(sheet_handler)))
    app.add_handler(CommandHandler("delete", _admin_only(delete_handler)))
    app.add_handler(CommandHandler("stock", _admin_only(stock_handler)))
    app.add_handler(CommandHandler("breakeven", _admin_only(breakeven_handler)))
    app.add_handler(CommandHandler("tomorrow", _admin_only(tomorrow_orders_handler)))

    # ── Текстовые сообщения: роутинг admin / customer ─────────────────────
    async def route_text(update, context):
        if _is_admin(update):
            await handle_message(update, context)
        else:
            await handle_customer_message(update, context)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_text))

    # ── Голосовые: только для администратора ─────────────────────────────
    async def route_voice(update, context):
        if _is_admin(update):
            await handle_voice(update, context)
        else:
            from src.handlers.keyboards import CUSTOMER_KEYBOARD

            await update.message.reply_text(
                "Голосовые доступны только администратору. Выбери этаж ниже.",
                reply_markup=CUSTOMER_KEYBOARD,
            )

    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, route_voice))

    # ── Фото: клиент → чек, администратор → игнорируем (пока) ────────────
    async def route_photo(update, context):
        if _is_admin(update):
            await update.message.reply_text(
                "📸 Фото получено. Для записи чека используй текст."
            )
        else:
            await handle_customer_photo(update, context)

    app.add_handler(MessageHandler(filters.PHOTO, route_photo))

    # ── Callback: выбор этажа клиентом ───────────────────────────────────
    app.add_handler(CallbackQueryHandler(handle_floor_callback, pattern=r"^floor:"))
    app.add_handler(
        CallbackQueryHandler(
            handle_order_tomorrow_callback,
            pattern=r"^order_tomorrow:",
        )
    )

    # ── Ежедневный отчёт в 22:00 Бишкек ─────────────────────────────────
    app.job_queue.run_daily(daily_report_job, time=DAILY_REPORT_TIME)

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
