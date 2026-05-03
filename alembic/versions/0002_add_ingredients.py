"""add ingredients

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("base_unit", sa.String(5), nullable=False),
        sa.Column("latest_price_per_unit", sa.Numeric(12, 6), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ingredient_purchases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ingredient_id", sa.Integer(),
                  sa.ForeignKey("ingredients.id"), nullable=False),
        sa.Column("quantity_base", sa.Numeric(12, 3), nullable=False),
        sa.Column("total_price_som", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(12, 6), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ingredient_purchases")
    op.drop_table("ingredients")
