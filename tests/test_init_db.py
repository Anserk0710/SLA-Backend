from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.constants import RoleName
from app.core.security import get_password_hash, verify_password
from app.db.base import Base
from app.db.init_db import SEED_USERS, seed_roles, seed_users
from app.models.role import Role
from app.models.user import User

TEST_DATABASE_URL = "sqlite://"


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _seeded_user_email(role_name: RoleName) -> str:
    for seed_user in SEED_USERS:
        if seed_user.role_name == role_name:
            return seed_user.email.strip().lower()
    raise AssertionError(f"Seed user untuk role {role_name.value} tidak ditemukan")


def _seeded_user_password(role_name: RoleName) -> str:
    for seed_user in SEED_USERS:
        if seed_user.role_name == role_name:
            return seed_user.password
    raise AssertionError(f"Seed user untuk role {role_name.value} tidak ditemukan")


def _seeded_user_name(role_name: RoleName) -> str:
    for seed_user in SEED_USERS:
        if seed_user.role_name == role_name:
            return seed_user.full_name
    raise AssertionError(f"Seed user untuk role {role_name.value} tidak ditemukan")


def test_seed_roles_creates_all_roles(db_session: Session) -> None:
    roles_by_name, created_roles = seed_roles(db_session)

    assert created_roles == len(RoleName)
    assert set(roles_by_name) == {role_name.value for role_name in RoleName}
    assert set(db_session.scalars(select(Role.name)).all()) == {
        role_name.value for role_name in RoleName
    }


def test_seed_users_creates_default_accounts_for_each_role(db_session: Session) -> None:
    roles_by_name, _ = seed_roles(db_session)
    created_users, updated_users = seed_users(db_session, roles_by_name)
    db_session.commit()

    assert created_users == len(SEED_USERS)
    assert updated_users == 0

    admin_user = db_session.scalar(
        select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL.strip().lower())
    )
    head_user = db_session.scalar(
        select(User).where(User.email == _seeded_user_email(RoleName.HEAD))
    )
    technician_user = db_session.scalar(
        select(User).where(User.email == _seeded_user_email(RoleName.TECHNICIAN))
    )

    assert admin_user is not None
    assert admin_user.role.name == RoleName.ADMIN.value
    assert verify_password(settings.FIRST_SUPERUSER_PASSWORD, admin_user.hashed_password)

    assert head_user is not None
    assert head_user.role.name == RoleName.HEAD.value
    assert verify_password(
        _seeded_user_password(RoleName.HEAD),
        head_user.hashed_password,
    )

    assert technician_user is not None
    assert technician_user.role.name == RoleName.TECHNICIAN.value
    assert verify_password(
        _seeded_user_password(RoleName.TECHNICIAN),
        technician_user.hashed_password,
    )


def test_seed_users_updates_existing_seeded_account(db_session: Session) -> None:
    roles_by_name, _ = seed_roles(db_session)
    db_session.add(
        User(
            full_name="Nama Lama",
            email=_seeded_user_email(RoleName.HEAD).upper(),
            hashed_password=get_password_hash("password-lama"),
            is_active=False,
            role_id=roles_by_name[RoleName.TECHNICIAN.value].id,
        )
    )
    db_session.commit()

    created_users, updated_users = seed_users(db_session, roles_by_name)
    db_session.commit()

    seeded_head_user = db_session.scalar(
        select(User).where(User.email == _seeded_user_email(RoleName.HEAD))
    )

    assert created_users == len(SEED_USERS) - 1
    assert updated_users == 1
    assert seeded_head_user is not None
    assert seeded_head_user.full_name == _seeded_user_name(RoleName.HEAD)
    assert seeded_head_user.is_active is True
    assert seeded_head_user.role.name == RoleName.HEAD.value
    assert verify_password(
        _seeded_user_password(RoleName.HEAD),
        seeded_head_user.hashed_password,
    )


def test_seed_users_is_idempotent_when_run_again(db_session: Session) -> None:
    roles_by_name, _ = seed_roles(db_session)
    seed_users(db_session, roles_by_name)
    db_session.commit()

    roles_by_name, created_roles = seed_roles(db_session)
    created_users, updated_users = seed_users(db_session, roles_by_name)
    db_session.commit()

    assert created_roles == 0
    assert created_users == 0
    assert updated_users == 0
