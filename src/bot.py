import logging
import os

from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

load_dotenv()

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    from src.handlers.commands import (
        cost_handler,
        day_handler,
        delete_handler,
        help_handler,
        month_handler,
        setprice_handler,
        sheet_handler,
        start_handler,
        week_handler,
    )
    from src.handlers.messages import handle_message

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("setprice", setprice_handler))
    app.add_handler(CommandHandler("day", day_handler))
    app.add_handler(CommandHandler("week", week_handler))
    app.add_handler(CommandHandler("month", month_handler))
    app.add_handler(CommandHandler("cost", cost_handler))
    app.add_handler(CommandHandler("sheet", sheet_handler))
    app.add_handler(CommandHandler("delete", delete_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
