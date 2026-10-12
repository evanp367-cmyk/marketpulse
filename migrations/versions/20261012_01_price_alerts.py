"""Add price alert state and delivery history without replacing existing rows.

Revision ID: 20261012_01
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "20261012_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "alert_rules" not in tables:
        raise RuntimeError("Existing MarketPulse tables must be initialized before alert migration")
    columns = {item["name"] for item in inspector.get_columns("alert_rules")}
    if "last_condition_met" not in columns:
        op.add_column("alert_rules", sa.Column("last_condition_met", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "alert_events" not in tables:
        op.create_table(
            "alert_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("rule_id", sa.Integer(), sa.ForeignKey("alert_rules.id", ondelete="SET NULL")),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("symbol", sa.String(30), nullable=False),
            sa.Column("price", sa.Numeric(28, 12), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("error", sa.String(200)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_alert_events_rule_id", "alert_events", ["rule_id"])
        op.create_index("ix_alert_events_user_id", "alert_events", ["user_id"])


def downgrade():
    op.drop_table("alert_events")
    op.drop_column("alert_rules", "last_condition_met")
