UNIT_TO_BASE = {
    "g": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "pcs": 1.0,
}

BASE_UNIT_FOR = {
    "g": "g",
    "kg": "g",
    "ml": "ml",
    "l": "ml",
    "pcs": "pcs",
}


def convert_to_base_unit(quantity: float, unit: str) -> float:
    return quantity * UNIT_TO_BASE.get(unit, 1.0)


def get_base_unit(unit: str) -> str:
    return BASE_UNIT_FOR.get(unit, unit)
