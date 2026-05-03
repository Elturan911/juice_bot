from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.event import Event


def get_floor_stock(session: Session) -> dict[int, int]:
    """
    Считает текущий остаток бутылок по каждому этажу.
    Логика: идём по событиям хронологически.
    manual_count — сбрасывает счётчик этажа до указанного значения.
    placement — прибавляет, sale и expiry_removal — вычитают.
    """
    events = session.scalars(
        select(Event)
        .where(Event.floor.isnot(None))
        .where(Event.event_type.in_([
            "placement", "sale", "expiry_removal", "manual_count"
        ]))
        .order_by(Event.event_date, Event.created_at)
    ).all()

    stock: dict[int, int] = {}

    for event in events:
        floor = event.floor
        qty = event.quantity or 0

        if event.event_type == "placement":
            stock[floor] = stock.get(floor, 0) + qty
        elif event.event_type in ("sale", "expiry_removal"):
            stock[floor] = stock.get(floor, 0) - qty
        elif event.event_type == "manual_count":
            stock[floor] = qty  # ручная сверка сбрасывает счётчик

    return {floor: max(0, count) for floor, count in sorted(stock.items())}


def format_stock_report(stock: dict[int, int]) -> str:
    if not stock:
        return "📭 Нет данных об остатках. Запиши размещение бутылок."

    lines = ["📦 Остатки по этажам:\n"]
    total = 0
    for floor, count in stock.items():
        emoji = "🟢" if count > 5 else "🟡" if count > 0 else "🔴"
        lines.append(f"{emoji} {floor}-й этаж: {count} шт")
        total += count

    lines.append(f"\n🍾 Всего: {total} шт")
    return "\n".join(lines)
