"""repair legacy integer ids to uuid strings

Revision ID: 3f3d8e3f7d44
Revises: 0f6cab88d96a
Create Date: 2026-04-04 11:45:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3f3d8e3f7d44"
down_revision: Union[str, Sequence[str], None] = "0f6cab88d96a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


STRING_ID = sa.String(length=36)


def _column_is_integer(bind: sa.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return isinstance(column["type"], sa.Integer)
    return False


def _fetch_rows(bind: sa.Connection, query: str) -> list[dict]:
    return [dict(row) for row in bind.execute(sa.text(query)).mappings().all()]


def _executemany(bind: sa.Connection, query: str, params: list[dict]) -> None:
    if params:
        bind.execute(sa.text(query), params)


def upgrade() -> None:
    bind = op.get_bind()
    if not _column_is_integer(bind, "roles", "id"):
        return

    role_rows = _fetch_rows(bind, "SELECT id, name FROM roles ORDER BY id")
    user_rows = _fetch_rows(
        bind,
        """
        SELECT id, full_name, email, hashed_password, is_active, role_id, created_at, updated_at
        FROM users
        ORDER BY id
        """,
    )
    ticket_rows = _fetch_rows(
        bind,
        """
        SELECT id, ticket_code, full_name, full_address, category, description, pic_name,
               phone_number, internal_status, public_status, created_at, updated_at
        FROM tickets
        ORDER BY id
        """,
    )
    assignment_rows = _fetch_rows(
        bind,
        """
        SELECT id, ticket_id, technician_user_id, assigned_by_user_id, assigned_at
        FROM ticket_assignments
        ORDER BY id
        """,
    )
    status_log_rows = _fetch_rows(
        bind,
        """
        SELECT id, ticket_id, old_status, new_status, notes, changed_by_user_id, changed_at
        FROM ticket_status_logs
        ORDER BY id
        """,
    )

    role_id_map = {row["id"]: str(uuid4()) for row in role_rows}
    user_id_map = {row["id"]: str(uuid4()) for row in user_rows}
    ticket_id_map = {row["id"]: str(uuid4()) for row in ticket_rows}
    assignment_id_map = {row["id"]: str(uuid4()) for row in assignment_rows}
    status_log_id_map = {row["id"]: str(uuid4()) for row in status_log_rows}

    op.drop_constraint("ticket_assignments_assigned_by_user_id_fkey", "ticket_assignments", type_="foreignkey")
    op.drop_constraint("ticket_assignments_technician_user_id_fkey", "ticket_assignments", type_="foreignkey")
    op.drop_constraint("ticket_assignments_ticket_id_fkey", "ticket_assignments", type_="foreignkey")
    op.drop_constraint("ticket_status_logs_changed_by_user_id_fkey", "ticket_status_logs", type_="foreignkey")
    op.drop_constraint("ticket_status_logs_ticket_id_fkey", "ticket_status_logs", type_="foreignkey")
    op.drop_constraint("users_role_id_fkey", "users", type_="foreignkey")
    op.drop_constraint("uq_ticket_technician", "ticket_assignments", type_="unique")

    op.drop_index("ix_ticket_assignments_technician_user_id", table_name="ticket_assignments")
    op.drop_index("ix_ticket_assignments_ticket_id", table_name="ticket_assignments")
    op.drop_index("ix_ticket_assignments_id", table_name="ticket_assignments")
    op.drop_index("ix_ticket_status_logs_ticket_id", table_name="ticket_status_logs")
    op.drop_index("ix_ticket_status_logs_id", table_name="ticket_status_logs")
    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_roles_id", table_name="roles")
    op.drop_index("ix_tickets_id", table_name="tickets")

    op.drop_constraint("ticket_assignments_pkey", "ticket_assignments", type_="primary")
    op.drop_constraint("ticket_status_logs_pkey", "ticket_status_logs", type_="primary")
    op.drop_constraint("users_pkey", "users", type_="primary")
    op.drop_constraint("roles_pkey", "roles", type_="primary")
    op.drop_constraint("tickets_pkey", "tickets", type_="primary")

    op.add_column("roles", sa.Column("id_v2", STRING_ID, nullable=True))

    op.add_column("users", sa.Column("id_v2", STRING_ID, nullable=True))
    op.add_column("users", sa.Column("role_id_v2", STRING_ID, nullable=True))

    op.add_column("tickets", sa.Column("id_v2", STRING_ID, nullable=True))

    op.add_column("ticket_assignments", sa.Column("id_v2", STRING_ID, nullable=True))
    op.add_column("ticket_assignments", sa.Column("ticket_id_v2", STRING_ID, nullable=True))
    op.add_column("ticket_assignments", sa.Column("technician_user_id_v2", STRING_ID, nullable=True))
    op.add_column("ticket_assignments", sa.Column("assigned_by_user_id_v2", STRING_ID, nullable=True))

    op.add_column("ticket_status_logs", sa.Column("id_v2", STRING_ID, nullable=True))
    op.add_column("ticket_status_logs", sa.Column("ticket_id_v2", STRING_ID, nullable=True))
    op.add_column("ticket_status_logs", sa.Column("changed_by_user_id_v2", STRING_ID, nullable=True))

    _executemany(
        bind,
        "UPDATE roles SET id_v2 = :new_id WHERE id = :old_id",
        [{"new_id": role_id_map[row["id"]], "old_id": row["id"]} for row in role_rows],
    )
    _executemany(
        bind,
        """
        UPDATE users
        SET id_v2 = :new_id,
            role_id_v2 = :new_role_id
        WHERE id = :old_id
        """,
        [
            {
                "new_id": user_id_map[row["id"]],
                "new_role_id": role_id_map[row["role_id"]],
                "old_id": row["id"],
            }
            for row in user_rows
        ],
    )
    _executemany(
        bind,
        "UPDATE tickets SET id_v2 = :new_id WHERE id = :old_id",
        [{"new_id": ticket_id_map[row["id"]], "old_id": row["id"]} for row in ticket_rows],
    )
    _executemany(
        bind,
        """
        UPDATE ticket_assignments
        SET id_v2 = :new_id,
            ticket_id_v2 = :new_ticket_id,
            technician_user_id_v2 = :new_technician_user_id,
            assigned_by_user_id_v2 = :new_assigned_by_user_id
        WHERE id = :old_id
        """,
        [
            {
                "new_id": assignment_id_map[row["id"]],
                "new_ticket_id": ticket_id_map[row["ticket_id"]],
                "new_technician_user_id": user_id_map[row["technician_user_id"]],
                "new_assigned_by_user_id": (
                    user_id_map[row["assigned_by_user_id"]]
                    if row["assigned_by_user_id"] is not None
                    else None
                ),
                "old_id": row["id"],
            }
            for row in assignment_rows
        ],
    )
    _executemany(
        bind,
        """
        UPDATE ticket_status_logs
        SET id_v2 = :new_id,
            ticket_id_v2 = :new_ticket_id,
            changed_by_user_id_v2 = :new_changed_by_user_id
        WHERE id = :old_id
        """,
        [
            {
                "new_id": status_log_id_map[row["id"]],
                "new_ticket_id": ticket_id_map[row["ticket_id"]],
                "new_changed_by_user_id": (
                    user_id_map[row["changed_by_user_id"]]
                    if row["changed_by_user_id"] is not None
                    else None
                ),
                "old_id": row["id"],
            }
            for row in status_log_rows
        ],
    )

    op.drop_column("ticket_assignments", "assigned_by_user_id")
    op.drop_column("ticket_assignments", "technician_user_id")
    op.drop_column("ticket_assignments", "ticket_id")
    op.drop_column("ticket_assignments", "id")

    op.drop_column("ticket_status_logs", "changed_by_user_id")
    op.drop_column("ticket_status_logs", "ticket_id")
    op.drop_column("ticket_status_logs", "id")

    op.drop_column("users", "role_id")
    op.drop_column("users", "id")

    op.drop_column("tickets", "id")
    op.drop_column("roles", "id")

    op.alter_column("roles", "id_v2", existing_type=STRING_ID, new_column_name="id")

    op.alter_column("users", "id_v2", existing_type=STRING_ID, new_column_name="id")
    op.alter_column("users", "role_id_v2", existing_type=STRING_ID, new_column_name="role_id")

    op.alter_column("tickets", "id_v2", existing_type=STRING_ID, new_column_name="id")

    op.alter_column("ticket_assignments", "id_v2", existing_type=STRING_ID, new_column_name="id")
    op.alter_column("ticket_assignments", "ticket_id_v2", existing_type=STRING_ID, new_column_name="ticket_id")
    op.alter_column(
        "ticket_assignments",
        "technician_user_id_v2",
        existing_type=STRING_ID,
        new_column_name="technician_user_id",
    )
    op.alter_column(
        "ticket_assignments",
        "assigned_by_user_id_v2",
        existing_type=STRING_ID,
        new_column_name="assigned_by_user_id",
    )

    op.alter_column("ticket_status_logs", "id_v2", existing_type=STRING_ID, new_column_name="id")
    op.alter_column("ticket_status_logs", "ticket_id_v2", existing_type=STRING_ID, new_column_name="ticket_id")
    op.alter_column(
        "ticket_status_logs",
        "changed_by_user_id_v2",
        existing_type=STRING_ID,
        new_column_name="changed_by_user_id",
    )

    op.alter_column("roles", "id", existing_type=STRING_ID, nullable=False)
    op.alter_column("users", "id", existing_type=STRING_ID, nullable=False)
    op.alter_column("users", "role_id", existing_type=STRING_ID, nullable=False)
    op.alter_column("tickets", "id", existing_type=STRING_ID, nullable=False)
    op.alter_column("ticket_assignments", "id", existing_type=STRING_ID, nullable=False)
    op.alter_column("ticket_assignments", "ticket_id", existing_type=STRING_ID, nullable=False)
    op.alter_column("ticket_assignments", "technician_user_id", existing_type=STRING_ID, nullable=False)
    op.alter_column("ticket_assignments", "assigned_by_user_id", existing_type=STRING_ID, nullable=True)
    op.alter_column("ticket_status_logs", "id", existing_type=STRING_ID, nullable=False)
    op.alter_column("ticket_status_logs", "ticket_id", existing_type=STRING_ID, nullable=False)
    op.alter_column("ticket_status_logs", "changed_by_user_id", existing_type=STRING_ID, nullable=True)

    op.create_primary_key("roles_pkey", "roles", ["id"])
    op.create_primary_key("users_pkey", "users", ["id"])
    op.create_primary_key("tickets_pkey", "tickets", ["id"])
    op.create_primary_key("ticket_assignments_pkey", "ticket_assignments", ["id"])
    op.create_primary_key("ticket_status_logs_pkey", "ticket_status_logs", ["id"])

    op.create_index("ix_roles_id", "roles", ["id"], unique=False)
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)
    op.create_index("ix_tickets_id", "tickets", ["id"], unique=False)
    op.create_index("ix_ticket_assignments_id", "ticket_assignments", ["id"], unique=False)
    op.create_index("ix_ticket_assignments_ticket_id", "ticket_assignments", ["ticket_id"], unique=False)
    op.create_index(
        "ix_ticket_assignments_technician_user_id",
        "ticket_assignments",
        ["technician_user_id"],
        unique=False,
    )
    op.create_index("ix_ticket_status_logs_id", "ticket_status_logs", ["id"], unique=False)
    op.create_index("ix_ticket_status_logs_ticket_id", "ticket_status_logs", ["ticket_id"], unique=False)

    op.create_unique_constraint(
        "uq_ticket_technician",
        "ticket_assignments",
        ["ticket_id", "technician_user_id"],
    )

    op.create_foreign_key("users_role_id_fkey", "users", "roles", ["role_id"], ["id"])
    op.create_foreign_key(
        "ticket_assignments_ticket_id_fkey",
        "ticket_assignments",
        "tickets",
        ["ticket_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "ticket_assignments_technician_user_id_fkey",
        "ticket_assignments",
        "users",
        ["technician_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "ticket_assignments_assigned_by_user_id_fkey",
        "ticket_assignments",
        "users",
        ["assigned_by_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "ticket_status_logs_ticket_id_fkey",
        "ticket_status_logs",
        "tickets",
        ["ticket_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "ticket_status_logs_changed_by_user_id_fkey",
        "ticket_status_logs",
        "users",
        ["changed_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade tidak didukung untuk migrasi repair schema legacy integer ke UUID string."
    )
