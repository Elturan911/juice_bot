from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.batch import Batch
from src.models.event import Event
from src.models.settings import get_setting


def get_day_analytics(session: Session, target_date: date) -> dict:
    return _get_period_analytics(session, target_date, target_date)


def get_prev_day_analytics(session: Session, target_date: date) -> dict:
    prev = target_date - timedelta(days=1)
    return _get_period_analytics(session, prev, prev)


def get_week_analytics(session: Session, any_date: date) -> dict:
    monday = any_date - timedelta(days=any_date.weekday())
    sunday = monday + timedelta(days=6)
    return _get_period_analytics(session, monday, sunday)


def get_prev_week_analytics(session: Session, any_date: date) -> dict:
    monday = any_date - timedelta(days=any_date.weekday())
    prev_monday = monday - timedelta(weeks=1)
    prev_sunday = prev_monday + timedelta(days=6)
    return _get_period_analytics(session, prev_monday, prev_sunday)


def get_month_analytics(session: Session, year: int, month: int) -> dict:
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
    return _get_period_analytics(session, start, end)


def get_prev_month_analytics(session: Session, year: int, month: int) -> dict:
    from calendar import monthrange
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    last_day = monthrange(prev_year, prev_month)[1]
    start = date(prev_year, prev_month, 1)
    end = date(prev_year, prev_month, last_day)
    return _get_period_analytics(session, start, end)


def _get_period_analytics(session: Session, start: date, end: date) -> dict:
    events = session.scalars(
        select(Event).where(Event.event_date.between(start, end))
    ).all()

    if not events:
        return {}

    bottle_price_str = get_setting(session, "bottle_price")
    bottle_price = float(bottle_price_str) if bottle_price_str else 0.0

    placed = sum(e.quantity or 0 for e in events if e.event_type == "placement")
    expiry = sum(e.quantity or 0 for e in events if e.event_type == "expiry_removal")
    expenses = sum(
        float(e.amount_som or 0)
        for e in events
        if e.event_type == "production_expense"
    )

    # продажи по этажам
    sales_by_floor: dict[int | None, int] = {}
    for e in events:
        if e.event_type == "sale":
            floor = e.floor
            sales_by_floor[floor] = sales_by_floor.get(floor, 0) + (e.quantity or 0)

    total_sold = sum(sales_by_floor.values())
    revenue = total_sold * bottle_price
    profit = revenue - expenses

    return {
        "start": start,
        "end": end,
        "placed": placed,
        "sold": total_sold,
        "expiry": expiry,
        "revenue": revenue,
        "expenses": expenses,
        "profit": profit,
        "bottle_price": bottle_price,
        "sales_by_floor": sales_by_floor,
    }


def _delta(current: float, previous: float) -> str:
    if previous == 0:
        return ""
    pct = (current - previous) / previous * 100
    arrow = "▲" if pct >= 0 else "▼"
    return f" {arrow}{abs(pct):.0f}%"


def format_period_report(analytics: dict, label: str, prev: dict | None = None) -> str:
    if not analytics:
        return "📭 За период нет записей."

    lines = [f"📊 {label}\n"]

    rev_delta = _delta(analytics["revenue"], prev["revenue"]) if prev else ""
    exp_delta = _delta(analytics["expenses"], prev["expenses"]) if prev else ""
    prf_delta = _delta(analytics["profit"], prev["profit"]) if prev else ""
    sol_delta = _delta(analytics["sold"], prev["sold"]) if prev else ""

    lines.append(f"💰 Выручка:   {analytics['revenue']:,.0f} сом{rev_delta}")
    lines.append(f"📉 Расходы:   {analytics['expenses']:,.0f} сом{exp_delta}")
    lines.append(f"✅ Прибыль:  {analytics['profit']:,.0f} сом{prf_delta}")
    lines.append(f"🍾 Продано:  {analytics['sold']} шт{sol_delta}")

    if analytics["sales_by_floor"]:
        lines.append("\nПо этажам:")
        for floor, qty in sorted(analytics["sales_by_floor"].items(), key=lambda x: x[0] or 0):
            floor_label = f"{floor}-й" if floor else "—"
            floor_rev = qty * analytics["bottle_price"]
            lines.append(f"  🏢 {floor_label} этаж: {qty} шт → {floor_rev:,.0f} сом")

    lines.append(f"\n📦 Размещено: {analytics['placed']} шт  |  🗑 Просрочка: {analytics['expiry']} шт")

    if prev:
        lines.append(f"\n(▲▼ vs предыдущий период)")

    return "\n".join(lines)


def get_breakeven_analysis(session: Session) -> dict:
    from calendar import monthrange
    today = date.today()
    year, month = today.year, today.month
    days_in_month = monthrange(year, month)[1]
    days_passed = today.day
    days_left = days_in_month - days_passed

    month_data = get_month_analytics(session, year, month)
    expenses = month_data.get("expenses", 0.0) if month_data else 0.0
    sold = month_data.get("sold", 0) if month_data else 0
    revenue = month_data.get("revenue", 0.0) if month_data else 0.0

    bottle_price_str = get_setting(session, "bottle_price")
    bottle_price = float(bottle_price_str) if bottle_price_str else 0.0

    cost_per_bottle = get_latest_batch_cost_per_bottle(session) or 0.0
    margin_per_bottle = bottle_price - cost_per_bottle

    breakeven_bottles = int(expenses / margin_per_bottle) + 1 if margin_per_bottle > 0 else None
    bottles_to_go = max(0, (breakeven_bottles or 0) - sold) if breakeven_bottles else None
    daily_pace = sold / days_passed if days_passed > 0 else 0
    projected_month = int(daily_pace * days_in_month)
    projected_revenue = projected_month * bottle_price
    projected_profit = projected_revenue - expenses

    return {
        "today": today,
        "days_passed": days_passed,
        "days_left": days_left,
        "days_in_month": days_in_month,
        "expenses": expenses,
        "sold": sold,
        "revenue": revenue,
        "bottle_price": bottle_price,
        "cost_per_bottle": cost_per_bottle,
        "margin_per_bottle": margin_per_bottle,
        "breakeven_bottles": breakeven_bottles,
        "bottles_to_go": bottles_to_go,
        "daily_pace": daily_pace,
        "projected_month": projected_month,
        "projected_revenue": projected_revenue,
        "projected_profit": projected_profit,
    }


def get_events_for_date(session: Session, target_date: date) -> list[Event]:
    return list(
        session.scalars(select(Event).where(Event.event_date == target_date)).all()
    )


def get_latest_batch_cost_per_bottle(session: Session) -> float | None:
    batch = session.scalars(
        select(Batch).order_by(Batch.created_at.desc()).limit(1)
    ).first()
    if batch and batch.cost_per_bottle_som:
        return float(batch.cost_per_bottle_som)
    return None
