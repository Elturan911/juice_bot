import json
import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from src.models.base import Session
from src.models.batch import save_batch
from src.models.batch_usage import BatchIngredientUsage
from src.models.event import delete_events_by_ids, save_events
from src.models.ingredient import get_or_create_ingredient
from src.models.ingredient_purchase import IngredientPurchase
from src.models.settings import delete_setting, get_setting, set_setting
from src.services.analytics import get_events_for_date
from src.services.cost_calculator import calculate_batch_cost, calculate_recommended_price
from src.services.market_price import get_or_fetch_market_price
from src.services.parser import parse_message
from src.services.schemas import EventType, ParsedMessage
from src.services.sheets import (
    append_to_expenses,
    append_to_profit,
    append_to_revenue,
)
from src.services.unit_converter import convert_to_base_unit, get_base_unit

logger = logging.getLogger(__name__)

UNKNOWN_HELP = (
    "❓ Не понял тип записи. Попробуй:\n\n"
    "Продажа: «продал 10 бутылок на 2ом этаже»\n"
    "Размещение: «разместил 15 бутылок на 3ем этаже»\n"
    "Расходы: «потратил 2000 сом на сахар»\n"
    "Закупка: «купил сахар 2 кг за 200 сом»\n"
    "Партия: «на партию ушло 500 г сахара, сварил 10 литров»"
)

EVENT_TYPE_LABELS = {
    "placement": "📦 Размещение",
    "sale": "💸 Продажа",
    "expiry_removal": "🗑 Просрочка",
    "manual_count": "📋 Остаток (сверка)",
    "production_expense": "📉 Расход",
}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    try:
        with Session() as session:
            # --- Проверка pending состояний ---
            pending_batch = get_setting(session, "pending_batch_text")
            pending_delete = get_setting(session, "pending_delete_ids")

            if pending_batch and _is_volume(text):
                await _handle_batch_volume_reply(update, session, pending_batch, text)
                return

            if pending_delete and _is_selection(text):
                await _handle_delete_selection(update, session, pending_delete, text)
                return

            # --- Парсинг нового сообщения ---
            parsed = parse_message(text)

            if parsed.event_type == EventType.UNKNOWN:
                await update.message.reply_text(UNKNOWN_HELP)
                return

            if parsed.event_type == EventType.INGREDIENT_PURCHASE:
                await _handle_ingredient_purchase(update, session, parsed, text)

            elif parsed.event_type == EventType.BATCH_USAGE:
                if not parsed.batch_usages:
                    await update.message.reply_text("❓ Укажи какие ингредиенты потратил.")
                    return
                if parsed.batch_volume_liters is None:
                    # Сохраняем ParsedMessage как JSON для повторного использования
                    pending_json = parsed.model_dump_json()
                    set_setting(session, "pending_batch_text", pending_json)
                    await update.message.reply_text(
                        "🍾 Сколько литров компота получилось из этих ингредиентов?\n"
                        "Ответь числом, например: «10»"
                    )
                else:
                    await _handle_batch_complete(update, session, parsed, text)

            else:
                await _handle_standard_event(update, session, parsed, text)

    except Exception as e:
        logger.error(f"handle_message error: {e}", exc_info=True)
        await update.message.reply_text("😔 Что-то пошло не так. Попробуй ещё раз.")


async def _handle_standard_event(update, session, parsed: ParsedMessage, raw_text: str):
    # Проверка цены для продаж
    if parsed.event_type == EventType.SALE:
        bottle_price = get_setting(session, "bottle_price")
        if not bottle_price:
            await update.message.reply_text(
                "⚠️ Сначала установи цену бутылки:\n/setprice 100"
            )
            return

    # Сохранение всех событий (включая additional_events)
    all_parsed = [parsed]
    if parsed.additional_events:
        all_parsed.extend(parsed.additional_events)

    saved_events = []
    for p in all_parsed:
        events = save_events(
            session,
            event_type=p.event_type.value,
            floor=p.floor,
            quantity=p.quantity,
            bottle_volume_ml=p.bottle_volume_ml,
            amount_som=p.amount_som,
            description=p.description,
            raw_text=raw_text,
            event_date=p.event_date,
        )
        saved_events.extend(events)

    # Формируем ответ
    reply_lines = ["✅ Записано:"]
    bottle_price_val = float(get_setting(session, "bottle_price") or 0)

    for event in saved_events:
        label = EVENT_TYPE_LABELS.get(event.event_type, event.event_type)
        line = f"\n{label}"
        if event.floor:
            line += f"\n🏢 Этаж: {event.floor}"
        if event.quantity:
            line += f"\n🍾 Бутылок: {event.quantity}"
        if event.event_type == "sale" and event.quantity and bottle_price_val:
            revenue = event.quantity * bottle_price_val
            line += f"\n💰 Выручка: {revenue:,.0f} сом"
        if event.amount_som:
            line += f"\n💳 Сумма: {float(event.amount_som):,.0f} сом"
        if event.description:
            line += f"\n📝 {event.description}"
        line += f"\n📅 {event.event_date.strftime('%d.%m.%Y')}"
        reply_lines.append(line)

    await update.message.reply_text("\n".join(reply_lines))

    # Sync to Google Sheets
    for event in saved_events:
        _sync_event_to_sheets(event, bottle_price_val)


async def _handle_ingredient_purchase(update, session, parsed: ParsedMessage, raw_text: str):
    if not all([parsed.ingredient_name, parsed.ingredient_quantity,
                parsed.ingredient_unit, parsed.ingredient_total_price_som]):
        await update.message.reply_text(
            "❓ Укажи название, количество и цену.\n"
            "Пример: «купил сахар 2 кг за 200 сом»"
        )
        return

    base_unit = get_base_unit(parsed.ingredient_unit)
    ingredient = get_or_create_ingredient(session, parsed.ingredient_name, base_unit)
    old_price = ingredient.latest_price_per_unit

    qty_base = convert_to_base_unit(parsed.ingredient_quantity, parsed.ingredient_unit)
    price_per_unit = parsed.ingredient_total_price_som / qty_base if qty_base > 0 else 0.0

    purchase = IngredientPurchase(
        ingredient_id=ingredient.id,
        quantity_base=qty_base,
        total_price_som=parsed.ingredient_total_price_som,
        price_per_unit=price_per_unit,
        raw_text=raw_text,
        purchase_date=date.today(),
    )
    session.add(purchase)
    ingredient.latest_price_per_unit = price_per_unit
    session.commit()

    unit_label = "г" if base_unit == "g" else "мл" if base_unit == "ml" else "шт"
    reply = (
        f"✅ Закупка записана:\n"
        f"🛒 {parsed.ingredient_name.capitalize()}: "
        f"{parsed.ingredient_quantity} {parsed.ingredient_unit} — "
        f"{parsed.ingredient_total_price_som:,.0f} сом\n"
        f"📊 Цена за {unit_label}: {price_per_unit:.4f} сом"
    )
    if old_price and abs(float(old_price) - price_per_unit) > 0.0001:
        reply += f"\n⚠️ Цена изменилась: {float(old_price):.4f} → {price_per_unit:.4f} сом/{unit_label}"

    await update.message.reply_text(reply)

    # Расходы в Sheets
    append_to_expenses(
        date.today(), "ingredient_purchase",
        f"{parsed.ingredient_name} {parsed.ingredient_quantity}{parsed.ingredient_unit}",
        parsed.ingredient_total_price_som,
    )


async def _handle_batch_volume_reply(update, session, pending_json: str, text: str):
    try:
        volume = float(text.replace(",", ".").split()[0])
    except ValueError:
        await update.message.reply_text("❓ Укажи число литров, например: «10»")
        return

    try:
        parsed = ParsedMessage.model_validate_json(pending_json)
        parsed.batch_volume_liters = volume
        delete_setting(session, "pending_batch_text")
        await _handle_batch_complete(update, session, parsed, f"(объём {volume} л)")
    except Exception as e:
        logger.error(f"batch volume reply error: {e}", exc_info=True)
        delete_setting(session, "pending_batch_text")
        await update.message.reply_text("😔 Не удалось обработать партию. Попробуй ещё раз.")


async def _handle_batch_complete(update, session, parsed: ParsedMessage, raw_text: str):
    calc = calculate_batch_cost(session, parsed)

    if "error" in calc:
        await update.message.reply_text(f"❌ {calc['error']}")
        return

    market_price = get_or_fetch_market_price(session)
    cost_per_bottle = calc["cost_per_bottle"]
    recommended = calculate_recommended_price(cost_per_bottle, market_price)
    margin = recommended - cost_per_bottle

    batch = save_batch(
        session,
        batch_date=date.today(),
        volume_liters=calc["volume_liters"],
        total_cost=calc["total_cost"],
        cost_per_liter=calc["cost_per_liter"],
        cost_per_bottle=cost_per_bottle,
        recommended_price=recommended,
        market_price=market_price,
        raw_text=raw_text,
    )

    # Сохранить расход ингредиентов
    for item in calc["itemized"]:
        usage = BatchIngredientUsage(
            batch_id=batch.id,
            ingredient_id=item["ingredient_id"],
            quantity_base=item["qty_base"],
            price_per_unit_used=item["price_per_unit"],
            cost_som=item["cost_som"],
        )
        session.add(usage)
    session.commit()

    lines = [f"✅ Партия от {date.today().strftime('%d.%m.%Y')} ({calc['volume_liters']} л):\n"]
    lines.append("Ингредиенты:")
    for item in calc["itemized"]:
        lines.append(
            f"  🔸 {item['name'].capitalize()} "
            f"{item['quantity']} {item['unit']} × "
            f"{item['price_per_unit']:.4f} сом = {item['cost_som']:.2f} сом"
        )
    if calc["missing"]:
        lines.append(f"\n⚠️ Нет данных о закупке: {', '.join(calc['missing'])}")

    lines.append(f"\n💸 Стоимость ингредиентов: {calc['total_cost']:,.2f} сом")
    lines.append(f"📉 Себестоимость 1 литра: {calc['cost_per_liter']:,.2f} сом")
    lines.append(f"🍾 Себестоимость бутылки 0.5 л: {cost_per_bottle:,.2f} сом")
    lines.append(f"\n🌐 Рыночная цена в Бишкеке: ~{market_price:,.0f} сом")
    lines.append(f"💡 Рекомендуемая цена: {recommended:,.0f} сом")
    margin_pct = (margin / cost_per_bottle * 100) if cost_per_bottle > 0 else 0
    lines.append(f"📈 Ваша маржа: {margin:,.2f} сом (+{margin_pct:.0f}%)")

    await update.message.reply_text("\n".join(lines))


async def _handle_delete_selection(update, session, pending_json: str, text: str):
    try:
        data = json.loads(pending_json)
        event_ids: list[int] = data["ids"]
        labels: list[str] = data["labels"]
    except Exception:
        delete_setting(session, "pending_delete_ids")
        await update.message.reply_text("❌ Ошибка. Повтори команду /delete.")
        return

    text_lower = text.lower().strip()
    if text_lower in ("нет", "no", "отмена", "cancel"):
        delete_setting(session, "pending_delete_ids")
        await update.message.reply_text("Отменено.")
        return

    if text_lower in ("да", "yes", "all", "все"):
        selected_ids = event_ids
    else:
        selected_ids = []
        for part in text.replace(",", " ").split():
            try:
                idx = int(part) - 1
                if 0 <= idx < len(event_ids):
                    selected_ids.append(event_ids[idx])
            except ValueError:
                pass

    if not selected_ids:
        await update.message.reply_text("❓ Укажи номера записей через запятую, например: «1, 3»")
        return

    deleted = delete_events_by_ids(session, selected_ids)
    delete_setting(session, "pending_delete_ids")
    await update.message.reply_text(f"✅ Удалено записей: {deleted}")


def _sync_event_to_sheets(event, bottle_price: float):
    try:
        if event.event_type == "sale" and event.quantity:
            revenue = event.quantity * bottle_price
            append_to_revenue(event.event_date, event.floor, event.quantity, revenue)
        elif event.event_type in ("production_expense",):
            append_to_expenses(
                event.event_date, event.event_type,
                event.description or "", float(event.amount_som or 0)
            )
    except Exception as e:
        logger.warning(f"Sheets sync failed silently: {e}")


def _is_volume(text: str) -> bool:
    try:
        val = float(text.replace(",", ".").split()[0])
        return val > 0
    except (ValueError, IndexError):
        return False


def _is_selection(text: str) -> bool:
    t = text.lower().strip()
    if t in ("да", "нет", "yes", "no", "все", "all", "отмена", "cancel"):
        return True
    parts = text.replace(",", " ").split()
    return all(p.isdigit() for p in parts) and len(parts) > 0
