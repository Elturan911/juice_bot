from src.services.schemas import ParsedMessage
from src.services.unit_converter import convert_to_base_unit, get_base_unit


def calculate_batch_cost(session, parsed: ParsedMessage) -> dict:
    from src.models.ingredient import Ingredient
    if not parsed.batch_usages:
        return {"error": "нет данных об ингредиентах"}

    itemized: list[dict] = []
    missing: list[str] = []
    total_cost = 0.0

    for usage in parsed.batch_usages:
        name = usage.ingredient_name.lower().strip()
        ingredient = session.query(Ingredient).filter_by(name=name).first()

        if not ingredient or ingredient.latest_price_per_unit is None:
            missing.append(usage.ingredient_name)
            continue

        qty_base = convert_to_base_unit(usage.quantity, usage.unit)
        cost = qty_base * float(ingredient.latest_price_per_unit)
        total_cost += cost

        itemized.append({
            "name": usage.ingredient_name,
            "quantity": usage.quantity,
            "unit": usage.unit,
            "qty_base": qty_base,
            "price_per_unit": float(ingredient.latest_price_per_unit),
            "cost_som": cost,
            "ingredient_id": ingredient.id,
        })

    volume = parsed.batch_volume_liters or 1.0
    cost_per_liter = total_cost / volume if volume > 0 else 0.0
    cost_per_bottle = cost_per_liter * 0.5

    return {
        "itemized": itemized,
        "missing": missing,
        "total_cost": total_cost,
        "volume_liters": volume,
        "cost_per_liter": cost_per_liter,
        "cost_per_bottle": cost_per_bottle,
    }


def calculate_recommended_price(cost_per_bottle: float, market_price: float) -> float:
    return max(cost_per_bottle * 2, market_price * 0.9)
