"""Signal subscriptions and independent Telegram delivery journal.

Revision ID: 20261012_03
Revises: 20261012_01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261012_03"
down_revision = "20261012_01"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "signal_subscriptions" not in tables:
        op.create_table(
            "signal_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("symbol", sa.String(30), nullable=False),
            sa.Column("interval", sa.String(3), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
            sa.Column("last_notified_at", sa.DateTime(timezone=True)),
            sa.Column("last_checked_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("user_id", "symbol", "interval", name="uq_signal_subscription"),
        )
        op.create_index("ix_signal_subscriptions_user_id", "signal_subscriptions", ["user_id"])
    if "signal_deliveries" not in tables:
        op.create_table(
            "signal_deliveries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("signal_subscriptions.id", ondelete="SET NULL")),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event_key", sa.String(150), nullable=False, unique=True),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("error", sa.String(200)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("delivered_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_signal_deliveries_subscription_id", "signal_deliveries", ["subscription_id"])
        op.create_index("ix_signal_deliveries_user_id", "signal_deliveries", ["user_id"])


def downgrade():
    op.drop_table("signal_deliveries")
    op.drop_table("signal_subscriptions")
