"""add tomorrow orders

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tomorrow_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tomorrow_orders_order_date", "tomorrow_orders", ["order_date"])
    op.create_index("ix_tomorrow_orders_customer", "tomorrow_orders", ["customer_chat_id"])


def downgrade() -> None:
    op.drop_index("ix_tomorrow_orders_customer", table_name="tomorrow_orders")
    op.drop_index("ix_tomorrow_orders_order_date", table_name="tomorrow_orders")
    op.drop_table("tomorrow_orders")
