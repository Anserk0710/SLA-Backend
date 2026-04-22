from dataclasses import dataclass

from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import RoleName
from app.core.security import get_password_hash, verify_password
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User


@dataclass(frozen=True)
class SeedUser:
    full_name: str
    email: str
    password: str
    role_name: RoleName
    is_active: bool = True


@dataclass(frozen=True)
class SeedSummary:
    created_roles: int
    created_users: int
    updated_users: int
    patched_ticket_schema: bool = False


SEED_USERS: tuple[SeedUser, ...] = (
    SeedUser(
        full_name="Super Admin",
        email=settings.FIRST_SUPERUSER_EMAIL,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        role_name=RoleName.ADMIN,
    ),
    SeedUser(
        full_name="Head SLA",
        email="head@example.com",
        password="head123",
        role_name=RoleName.HEAD,
    ),
    SeedUser(
        full_name="Teknisi SLA",
        email="technician@example.com",
        password="technician123",
        role_name=RoleName.TECHNICIAN,
    ),
)


def seed_roles(db: Session) -> tuple[dict[str, Role], int]:
    roles_by_name = {
        role.name: role
        for role in db.scalars(select(Role)).all()
    }
    created_roles = 0

    for role_name in RoleName:
        role = roles_by_name.get(role_name.value)
        if role is not None:
            continue

        role = Role(name=role_name.value)
        db.add(role)
        db.flush()
        roles_by_name[role.name] = role
        created_roles += 1

    return roles_by_name, created_roles


def _password_matches(plain_password: str, hashed_password: str) -> bool:
    try:
        return verify_password(plain_password, hashed_password)
    except Exception:
        return False


def seed_users(db: Session, roles_by_name: dict[str, Role]) -> tuple[int, int]:
    created_users = 0
    updated_users = 0

    for seed_user in SEED_USERS:
        normalized_email = seed_user.email.strip().lower()
        role = roles_by_name[seed_user.role_name.value]
        existing_user = db.scalar(
            select(User).where(func.lower(User.email) == normalized_email)
        )

        if existing_user is None:
            db.add(
                User(
                    full_name=seed_user.full_name,
                    email=normalized_email,
                    hashed_password=get_password_hash(seed_user.password),
                    is_active=seed_user.is_active,
                    role_id=role.id,
                )
            )
            created_users += 1
            continue

        user_changed = False

        if existing_user.full_name != seed_user.full_name:
            existing_user.full_name = seed_user.full_name
            user_changed = True

        if existing_user.email != normalized_email:
            existing_user.email = normalized_email
            user_changed = True

        if existing_user.is_active != seed_user.is_active:
            existing_user.is_active = seed_user.is_active
            user_changed = True

        if existing_user.role_id != role.id:
            existing_user.role_id = role.id
            user_changed = True

        if not _password_matches(seed_user.password, existing_user.hashed_password):
            existing_user.hashed_password = get_password_hash(seed_user.password)
            user_changed = True

        if user_changed:
            updated_users += 1

    return created_users, updated_users


def _has_column(db: Session, table_name: str, column_name: str) -> bool:
    bind = db.get_bind()
    if bind is None:
        return False

    inspector = inspect(bind)
    if table_name not in set(inspector.get_table_names()):
        return False

    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def ensure_ticket_schema(db: Session) -> bool:
    bind = db.get_bind()
    if bind is None:
        return False

    inspector = inspect(bind)
    if "tickets" not in set(inspector.get_table_names()):
        return False

    if _has_column(db, "tickets", "item_name"):
        return False

    try:
        db.execute(
            text(
                "ALTER TABLE tickets "
                "ADD COLUMN item_name VARCHAR(150) NOT NULL DEFAULT ''"
            )
        )
    except SQLAlchemyError:
        # Bisa terjadi jika instance lain sudah lebih dulu menambahkan kolom ini.
        if _has_column(db, "tickets", "item_name"):
            return False
        raise

    if bind.dialect.name in {"postgresql", "mysql"}:
        try:
            db.execute(
                text(
                    "ALTER TABLE tickets "
                    "ALTER COLUMN item_name DROP DEFAULT"
                )
            )
        except SQLAlchemyError:
            # Default kosong tetap aman dipakai; ini hanya merapikan schema.
            pass

    return True


def init_db() -> SeedSummary:
    db = SessionLocal()
    try:
        patched_ticket_schema = ensure_ticket_schema(db)
        roles_by_name, created_roles = seed_roles(db)
        created_users, updated_users = seed_users(db, roles_by_name)
        db.commit()
        return SeedSummary(
            created_roles=created_roles,
            created_users=created_users,
            updated_users=updated_users,
            patched_ticket_schema=patched_ticket_schema,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    summary = init_db()
    print(
        "Seed selesai. "
        f"Role baru: {summary.created_roles}, "
        f"User baru: {summary.created_users}, "
        f"User diupdate: {summary.updated_users}."
    )
