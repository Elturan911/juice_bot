"""add batches

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "batches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_date", sa.Date(), nullable=False),
        sa.Column("volume_liters", sa.Numeric(6, 2), nullable=False),
        sa.Column("total_ingredient_cost_som", sa.Numeric(10, 2), nullable=True),
        sa.Column("cost_per_liter_som", sa.Numeric(10, 2), nullable=True),
        sa.Column("cost_per_bottle_som", sa.Numeric(10, 2), nullable=True),
        sa.Column("recommended_price_som", sa.Numeric(10, 2), nullable=True),
        sa.Column("market_price_used_som", sa.Numeric(10, 2), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "batch_ingredient_usages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.Integer(),
                  sa.ForeignKey("batches.id"), nullable=False),
        sa.Column("ingredient_id", sa.Integer(),
                  sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("quantity_base", sa.Numeric(12, 3), nullable=False),
        sa.Column("price_per_unit_used", sa.Numeric(12, 6), nullable=False),
        sa.Column("cost_som", sa.Numeric(10, 2), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("batch_ingredient_usages")
    op.drop_table("batches")
