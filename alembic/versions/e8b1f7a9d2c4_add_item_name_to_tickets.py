"""add item name to tickets

Revision ID: e8b1f7a9d2c4
Revises: 9f3c8d4e2b11
Create Date: 2026-04-22 15:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8b1f7a9d2c4"
down_revision: Union[str, Sequence[str], None] = "9f3c8d4e2b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "tickets",
        sa.Column(
            "item_name",
            sa.String(length=150),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.alter_column("tickets", "item_name", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tickets", "item_name")

