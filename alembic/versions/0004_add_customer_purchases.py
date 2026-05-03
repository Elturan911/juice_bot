"""add customer purchases

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_purchases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("amount_som", sa.Numeric(10, 2), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(10), nullable=False, server_default="text"),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cp_purchase_date", "customer_purchases", ["purchase_date"])
    op.create_index("ix_cp_customer", "customer_purchases", ["customer_chat_id"])


def downgrade() -> None:
    op.drop_table("customer_purchases")
