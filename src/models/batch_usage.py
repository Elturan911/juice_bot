from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import mapped_column, relationship

from .base import Base


class BatchIngredientUsage(Base):
    __tablename__ = "batch_ingredient_usages"

    id: int = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: int = mapped_column(Integer, ForeignKey("batches.id"), nullable=False)
    ingredient_id: int = mapped_column(Integer, ForeignKey("ingredients.id"), nullable=False)
    quantity_base: float = mapped_column(Numeric(12, 3), nullable=False)
    price_per_unit_used: float = mapped_column(Numeric(12, 6), nullable=False)
    cost_som: float = mapped_column(Numeric(10, 2), nullable=False)

    batch = relationship("Batch")
    ingredient = relationship("Ingredient")
