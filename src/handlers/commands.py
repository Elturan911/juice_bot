import json
import logging
import os
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from src.models.base import Session
from src.models.batch import Batch
from src.models.settings import get_setting, set_setting
from src.services.analytics import (
    format_period_report,
    get_day_analytics,
    get_events_for_date,
    get_month_analytics,
    get_week_analytics,
)

logger = logging.getLogger(__name__)

EVENT_TYPE_RU = {
    "placement": "Размещение",
    "sale": "Продажа",
    "expiry_removal": "Просрочка",
    "manual_count": "Остаток",
    "production_expense": "Расход",
    "ingredient_purchase": "Закупка",
    "batch_usage": "Партия",
}


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я помогу вести учёт продаж компота 🍹\n\n"
        "Просто пиши мне что происходит:\n"
        "• «продал 10 бутылок на 2ом этаже»\n"
        "• «разместил 15 бутылок на 3ем этаже»\n"
        "• «купил сахар 2 кг за 200 сом»\n"
        "• «на партию ушло 500 г сахара, сварил 10 литров»\n\n"
        "Сначала установи цену бутылки: /setprice 100\n\n"
        "Все команды: /help"
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🍹 juice_bot — учёт компота\n\n"
        "Пиши в свободной форме или используй команды:\n\n"
        "/setprice <сумма>       — цена продажи бутылки\n"
        "/setmarketprice <сумма> — рыночная цена в Бишкеке\n"
        "/day [дата]             — отчёт за день\n"
        "/week [дата]            — отчёт за неделю\n"
        "/month [месяц]          — отчёт за месяц\n"
        "/cost                   — последняя себестоимость\n"
        "/sheet                  — ссылка на таблицу\n"
        "/delete <дата>          — удалить записи за дату\n"
        "/help                   — эта справка"
    )


async def setprice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("❌ Укажи цену: /setprice 100")
        return
    try:
        price = float(args[0].replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Укажи цену числом: /setprice 100")
        return

    with Session() as session:
        set_setting(session, "bottle_price", str(price))

    await update.message.reply_text(
        f"✅ Цена установлена: {price:,.0f} сом/бутылка\n"
        "Все следующие расчёты выручки будут по этой цене."
    )


async def day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target = _parse_date_arg(context.args)
    if target is None:
        await update.message.reply_text("❌ Формат даты: /day 2026-05-04")
        return

    with Session() as session:
        analytics = get_day_analytics(session, target)

    label = f"Отчёт за {target.strftime('%d %B %Y').lower()}"
    await update.message.reply_text(format_period_report(analytics, label))


async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target = _parse_date_arg(context.args)
    if target is None:
        await update.message.reply_text("❌ Формат: /week 2026-05-04")
        return

    with Session() as session:
        analytics = get_week_analytics(session, target)

    if analytics:
        start = analytics["start"]
        end = analytics["end"]
        label = f"Неделя {start.strftime('%d.%m')} — {end.strftime('%d.%m.%Y')}"
    else:
        label = "неделя"
    await update.message.reply_text(format_period_report(analytics, label))


async def month_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        today = date.today()
        year, month = today.year, today.month
    else:
        try:
            parts = args[0].split("-")
            year, month = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            await update.message.reply_text("❌ Формат: /month 2026-05")
            return

    with Session() as session:
        analytics = get_month_analytics(session, year, month)

    import calendar
    month_name = calendar.month_name[month]
    label = f"{month_name} {year}"
    await update.message.reply_text(format_period_report(analytics, label))


async def cost_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from sqlalchemy import select
    with Session() as session:
        batch = session.scalars(
            select(Batch).order_by(Batch.created_at.desc()).limit(1)
        ).first()

    if not batch:
        await update.message.reply_text("📭 Нет данных о партиях. Запиши расход ингредиентов.")
        return

    margin = (float(batch.recommended_price_som or 0) -
              float(batch.cost_per_bottle_som or 0))
    cost = float(batch.cost_per_bottle_som or 0)
    pct = (margin / cost * 100) if cost > 0 else 0

    await update.message.reply_text(
        f"📋 Последняя партия ({batch.batch_date.strftime('%d.%m.%Y')}, "
        f"{batch.volume_liters} л):\n\n"
        f"🍾 Себестоимость бутылки: {cost:,.2f} сом\n"
        f"🌐 Рыночная цена: ~{float(batch.market_price_used_som or 0):,.0f} сом\n"
        f"💡 Рекомендуемая цена: {float(batch.recommended_price_som or 0):,.0f} сом\n"
        f"📈 Маржа: {margin:,.2f} сом (+{pct:.0f}%)"
    )


async def setmarketprice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        with Session() as session:
            from src.services.market_price import get_or_fetch_market_price
            current = get_or_fetch_market_price(session)
        await update.message.reply_text(
            f"📊 Текущая рыночная цена: {current:,.0f} сом/бутылка\n"
            "Чтобы изменить: /setmarketprice 120"
        )
        return
    try:
        price = float(args[0].replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Укажи цену числом: /setmarketprice 120")
        return

    with Session() as session:
        from src.services.market_price import set_market_price
        set_market_price(session, price)

    await update.message.reply_text(
        f"✅ Рыночная цена обновлена: {price:,.0f} сом/бутылка\n"
        "Используется для расчёта рекомендованной цены."
    )


async def sheet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    spreadsheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID", "")
    if spreadsheet_id:
        url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        await update.message.reply_text(f"📊 Google Таблица:\n{url}")
    else:
        await update.message.reply_text("⚠️ ID таблицы не настроен.")


async def delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    delete_all = False

    if not args:
        await update.message.reply_text(
            "❌ Укажи дату: /delete 2026-05-04\n"
            "Или все записи за дату: /delete all 2026-05-04"
        )
        return

    if args[0].lower() == "all" and len(args) >= 2:
        delete_all = True
        date_str = args[1]
    else:
        date_str = args[0]

    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        await update.message.reply_text("❌ Формат даты: /delete 2026-05-04")
        return

    with Session() as session:
        events = get_events_for_date(session, target)

        if not events:
            await update.message.reply_text(
                f"📭 За {target.strftime('%d.%m.%Y')} нет записей."
            )
            return

        if delete_all:
            lines = [f"⚠️ Удалить ВСЕ {len(events)} записей за {target.strftime('%d.%m.%Y')}?\n"]
            for i, e in enumerate(events, 1):
                label = EVENT_TYPE_RU.get(e.event_type, e.event_type)
                lines.append(f"{i}. {label} — {e.quantity or ''} {e.amount_som or ''}")
            lines.append("\nОтветь «Да» или «Нет»")
            pending = {"ids": [e.id for e in events], "labels": [], "all": True}
        else:
            lines = [f"📋 Записи за {target.strftime('%d.%m.%Y')}:\n"]
            labels = []
            for i, e in enumerate(events, 1):
                label = EVENT_TYPE_RU.get(e.event_type, e.event_type)
                detail = ""
                if e.floor:
                    detail += f" этаж {e.floor}"
                if e.quantity:
                    detail += f" {e.quantity} шт"
                if e.amount_som:
                    detail += f" {float(e.amount_som):,.0f} сом"
                line = f"{i}. {label}{detail}"
                lines.append(line)
                labels.append(line)
            lines.append("\nВведи номера для удаления (через запятую): «1» или «1, 3»")
            pending = {"ids": [e.id for e in events], "labels": labels}

        set_setting(session, "pending_delete_ids", json.dumps(pending))

    await update.message.reply_text("\n".join(lines))


def _parse_date_arg(args) -> date | None:
    if not args:
        return date.today()
    try:
        return date.fromisoformat(args[0])
    except ValueError:
        return None
