from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.batch import Batch
from src.models.event import Event
from src.models.settings import get_setting


def get_day_analytics(session: Session, target_date: date) -> dict:
    return _get_period_analytics(session, target_date, target_date)


def get_week_analytics(session: Session, any_date: date) -> dict:
    monday = any_date - timedelta(days=any_date.weekday())
    sunday = monday + timedelta(days=6)
    return _get_period_analytics(session, monday, sunday)


def get_month_analytics(session: Session, year: int, month: int) -> dict:
    from calendar import monthrange
    last_day = monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)
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


def format_period_report(analytics: dict, label: str) -> str:
    if not analytics:
        return f"📭 За период нет записей."

    lines = [f"📊 {label}\n"]
    lines.append(f"💰 Выручка:    {analytics['revenue']:,.0f} сом")
    lines.append(f"📉 Расходы:    {analytics['expenses']:,.0f} сом")
    lines.append(f"✅ Прибыль:   {analytics['profit']:,.0f} сом")

    if analytics["sales_by_floor"]:
        lines.append("\nПо этажам:")
        for floor, qty in sorted(analytics["sales_by_floor"].items(), key=lambda x: x[0] or 0):
            floor_label = f"{floor}-й" if floor else "—"
            floor_rev = qty * analytics["bottle_price"]
            lines.append(f"  🏢 {floor_label} этаж: {qty} шт → {floor_rev:,.0f} сом")

    lines.append(f"\n🍾 Размещено: {analytics['placed']} шт  |  🗑 Просрочка: {analytics['expiry']} шт")
    return "\n".join(lines)


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
