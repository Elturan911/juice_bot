from telegram import KeyboardButton, ReplyKeyboardMarkup

BTN_TODAY = "📊 Сегодня"
BTN_WEEK = "📅 Неделя"
BTN_MONTH = "🗓 Месяц"
BTN_COST = "💸 Себестоимость"
BTN_SHEET = "📋 Таблица"
BTN_SET_PRICE = "💰 Цена продажи"
BTN_MARKET_PRICE = "🌐 Рыночная цена"
BTN_HELP = "❓ Помощь"

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [BTN_TODAY, BTN_WEEK, BTN_MONTH],
        [BTN_COST, BTN_SHEET],
        [BTN_SET_PRICE, BTN_MARKET_PRICE],
        [BTN_HELP],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

ALL_BUTTONS = {BTN_TODAY, BTN_WEEK, BTN_MONTH, BTN_COST,
               BTN_SHEET, BTN_SET_PRICE, BTN_MARKET_PRICE, BTN_HELP}
