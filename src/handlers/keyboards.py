from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# ── Кнопки администратора ──────────────────────────────────────────────────
BTN_TODAY = "📊 Сегодня"
BTN_WEEK = "📅 Неделя"
BTN_MONTH = "🗓 Месяц"
BTN_STOCK = "📦 Остатки"
BTN_COST = "💸 Себестоимость"
BTN_SHEET = "📋 Таблица"
BTN_SET_PRICE = "💰 Цена продажи"
BTN_MARKET_PRICE = "🌐 Рыночная цена"
BTN_HELP = "❓ Помощь"

ADMIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [BTN_TODAY, BTN_WEEK, BTN_MONTH],
        [BTN_STOCK, BTN_COST, BTN_SHEET],
        [BTN_SET_PRICE, BTN_MARKET_PRICE],
        [BTN_HELP],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Обратная совместимость
MAIN_KEYBOARD = ADMIN_KEYBOARD

ADMIN_BUTTONS = {BTN_TODAY, BTN_WEEK, BTN_MONTH, BTN_COST,
                 BTN_SHEET, BTN_SET_PRICE, BTN_MARKET_PRICE, BTN_HELP, BTN_STOCK}
ALL_BUTTONS = ADMIN_BUTTONS  # для обратной совместимости

# ── Кнопки клиента ────────────────────────────────────────────────────────
BTN_C_STOCK = "🍾 Сколько бутылок осталось?"
BTN_C_BUY = "✅ Я купил компот"

CUSTOMER_KEYBOARD = ReplyKeyboardMarkup(
    [
        [BTN_C_STOCK],
        [BTN_C_BUY],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

CUSTOMER_BUTTONS = {BTN_C_STOCK, BTN_C_BUY}

# ── Inline-кнопки выбора этажа ────────────────────────────────────────────
FLOOR_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🏢 2-й этаж", callback_data="floor:2"),
        InlineKeyboardButton("🏢 3-й этаж", callback_data="floor:3"),
    ]
])
