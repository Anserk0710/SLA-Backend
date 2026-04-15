"""phase 5 business features

Revision ID: 9f3c8d4e2b11
Revises: 558ae9bdc4b1
Create Date: 2026-04-13 00:00:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f3c8d4e2b11"
down_revision: Union[str, Sequence[str], None] = "558ae9bdc4b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("tickets", sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "tickets",
        sa.Column(
            "is_sla_breached",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_tickets_sla_deadline", "tickets", ["sla_deadline"], unique=False)
    op.create_index("ix_tickets_is_sla_breached", "tickets", ["is_sla_breached"], unique=False)

    op.create_table(
        "sla_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("hours_target", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sla_policies_id", "sla_policies", ["id"], unique=False)
    op.create_index("ix_sla_policies_category", "sla_policies", ["category"], unique=True)

    sla_table = sa.table(
        "sla_policies",
        sa.column("id", sa.String(length=36)),
        sa.column("category", sa.String(length=100)),
        sa.column("hours_target", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )

    op.bulk_insert(
        sla_table,
        [
            {"id": str(uuid4()), "category": "Critical", "hours_target": 2, "is_active": True},
            {"id": str(uuid4()), "category": "High", "hours_target": 4, "is_active": True},
            {"id": str(uuid4()), "category": "Medium", "hours_target": 8, "is_active": True},
            {"id": str(uuid4()), "category": "Low", "hours_target": 24, "is_active": True},
        ],
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ticket_id",
            sa.String(length=36),
            sa.ForeignKey("tickets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False, server_default=sa.text("'INFO'")),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_ticket_id", "notifications", ["ticket_id"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_ticket_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_sla_policies_category", table_name="sla_policies")
    op.drop_index("ix_sla_policies_id", table_name="sla_policies")
    op.drop_table("sla_policies")

    op.drop_index("ix_tickets_is_sla_breached", table_name="tickets")
    op.drop_index("ix_tickets_sla_deadline", table_name="tickets")
    op.drop_column("tickets", "is_sla_breached")
    op.drop_column("tickets", "sla_deadline")
