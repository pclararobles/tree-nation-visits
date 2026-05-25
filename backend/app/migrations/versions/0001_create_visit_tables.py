from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_create_visit_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_customer_id", sa.String(length=128), nullable=False),
        sa.Column("visit_count", sa.Integer(), nullable=False),
        sa.Column("trees_planted", sa.Integer(), nullable=False),
        sa.Column("last_connection_at", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_customers_external_customer_id",
        "customers",
        ["external_customer_id"],
        unique=True,
    )
    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_visits_occurred_at", "visits", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("idx_visits_occurred_at", table_name="visits")
    op.drop_table("visits")
    op.drop_index("ix_customers_external_customer_id", table_name="customers")
    op.drop_table("customers")
