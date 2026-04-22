from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints import technician as technician_endpoint_module
from app.core.config import settings
from app.core.constants import RoleName, TicketStatus
from app.core.permissions import (
    ensure_assign_permission,
    ensure_dashboard_permission,
    ensure_technician_only,
    ensure_ticket_visible_to_user,
    get_role_name,
)
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.user import User


def _build_user_with_role(role_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        id="user-123",
        role=SimpleNamespace(name=role_name),
    )


def _get_or_create_role(db_session: Session, role_name: RoleName) -> Role:
    role = db_session.scalar(select(Role).where(Role.name == role_name.value))
    if role is not None:
        return role

    role = Role(name=role_name.value)
    db_session.add(role)
    db_session.flush()
    return role


def test_get_role_name_supports_multiple_user_shapes() -> None:
    assert get_role_name(SimpleNamespace(role_name="  Technician  ")) == RoleName.TECHNICIAN.value
    assert get_role_name(SimpleNamespace(role=SimpleNamespace(name="HEAD"))) == RoleName.HEAD.value
    assert get_role_name(SimpleNamespace(role="admin")) == RoleName.ADMIN.value
    assert get_role_name(SimpleNamespace()) is None


def test_permission_helpers_reject_wrong_roles() -> None:
    technician_user = _build_user_with_role(RoleName.TECHNICIAN.value)
    admin_user = _build_user_with_role(RoleName.ADMIN.value)

    with pytest.raises(HTTPException, match="assign teknisi"):
        ensure_assign_permission(technician_user)

    with pytest.raises(HTTPException, match="dashboard operasional"):
        ensure_dashboard_permission(technician_user)

    with pytest.raises(HTTPException, match="Hanya teknisi"):
        ensure_technician_only(admin_user)


def test_ensure_ticket_visible_to_user_allows_admin_and_assigned_technician(
    db_session: Session,
) -> None:
    admin_user = db_session.scalar(select(User))
    assert admin_user is not None

    technician_role = _get_or_create_role(db_session, RoleName.TECHNICIAN)
    technician = User(
        full_name="Teknisi Visibility",
        email="teknisi.visibility@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-RBAC-001",
        full_name="Akses Teknisi",
        full_address="Jl. Akses No. 1",
        category="Internet",
        description="Uji akses ticket.",
        pic_name="PIC RBAC",
        phone_number="081200000301",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
    )
    db_session.add_all([technician, ticket])
    db_session.flush()
    db_session.add(
        TicketAssignment(
            ticket_id=ticket.id,
            technician_user_id=technician.id,
        )
    )
    db_session.commit()

    ensure_ticket_visible_to_user(db_session, ticket.id, admin_user)
    ensure_ticket_visible_to_user(db_session, ticket.id, technician)


def test_ensure_ticket_visible_to_user_rejects_unassigned_technician(
    db_session: Session,
) -> None:
    technician_role = _get_or_create_role(db_session, RoleName.TECHNICIAN)
    technician = User(
        full_name="Teknisi Tanpa Assignment",
        email="teknisi.no-access@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-RBAC-002",
        full_name="Akses Ditolak",
        full_address="Jl. Akses No. 2",
        category="CCTV",
        description="Uji akses ticket ditolak.",
        pic_name="PIC Ditolak",
        phone_number="081200000302",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
    )
    db_session.add_all([technician, ticket])
    db_session.commit()

    with pytest.raises(HTTPException, match="Anda tidak berhak mengakses ticket ini."):
        ensure_ticket_visible_to_user(db_session, ticket.id, technician)


def test_dashboard_endpoint_forbidden_for_technician(
    client: TestClient,
    db_session: Session,
) -> None:
    technician_role = _get_or_create_role(db_session, RoleName.TECHNICIAN)
    technician = User(
        full_name="Teknisi Dashboard",
        email="teknisi.dashboard.rbac@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    db_session.add(technician)
    db_session.commit()

    client.app.dependency_overrides[get_current_user] = lambda: technician
    try:
        response = client.get(f"{settings.API_V1_PREFIX}/dashboard/summary")
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Hanya admin/head yang boleh membuka dashboard operasional.",
    }


def test_check_in_endpoint_blocks_unassigned_technician_before_upload(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technician_role = _get_or_create_role(db_session, RoleName.TECHNICIAN)
    current_technician = User(
        full_name="Teknisi Current",
        email="teknisi.current@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    assigned_technician = User(
        full_name="Teknisi Assigned",
        email="teknisi.assigned@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-RBAC-003",
        full_name="Upload Harus Ditolak",
        full_address="Jl. Akses No. 3",
        category="Internet",
        description="Pastikan upload tidak berjalan jika tidak berhak.",
        pic_name="PIC Upload",
        phone_number="081200000303",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
    )
    db_session.add_all([current_technician, assigned_technician, ticket])
    db_session.flush()
    db_session.add(
        TicketAssignment(
            ticket_id=ticket.id,
            technician_user_id=assigned_technician.id,
        )
    )
    db_session.commit()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("upload_checkin_photo tidak boleh dipanggil untuk user yang tidak berhak")

    monkeypatch.setattr(technician_endpoint_module, "upload_checkin_photo", fail_if_called)

    client.app.dependency_overrides[get_current_user] = lambda: current_technician
    try:
        response = client.post(
            f"{settings.API_V1_PREFIX}/technician/tickets/{ticket.id}/check-in",
            data={
                "latitude": "1.234",
                "longitude": "2.345",
                "address": "Lokasi uji",
                "notes": "Catatan uji",
            },
            files={
                "photo": ("arrival.jpg", BytesIO(b"fake-image-content"), "image/jpeg"),
            },
        )
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Anda tidak berhak mengakses ticket ini.",
    }


def test_check_in_endpoint_rejects_invalid_photo_before_upload(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    technician_role = _get_or_create_role(db_session, RoleName.TECHNICIAN)
    technician = User(
        full_name="Teknisi Validasi File",
        email="teknisi.file@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-RBAC-004",
        full_name="Upload Invalid",
        full_address="Jl. Akses No. 4",
        category="Internet",
        description="Pastikan validasi file berjalan sebelum upload.",
        pic_name="PIC Invalid",
        phone_number="081200000304",
        internal_status=TicketStatus.ASSIGNED.value,
        public_status="Sedang Dikerjakan",
    )
    db_session.add_all([technician, ticket])
    db_session.flush()
    db_session.add(
        TicketAssignment(
            ticket_id=ticket.id,
            technician_user_id=technician.id,
        )
    )
    db_session.commit()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("upload_checkin_photo tidak boleh dipanggil untuk file yang tidak valid")

    monkeypatch.setattr(technician_endpoint_module, "upload_checkin_photo", fail_if_called)

    client.app.dependency_overrides[get_current_user] = lambda: technician
    try:
        response = client.post(
            f"{settings.API_V1_PREFIX}/technician/tickets/{ticket.id}/check-in",
            data={
                "latitude": "1.234",
                "longitude": "2.345",
                "address": "Lokasi uji",
                "notes": "Catatan uji",
            },
            files={
                "photo": ("arrival.gif", BytesIO(b"fake-image-content"), "image/gif"),
            },
        )
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Ekstensi file foto tidak didukung.",
    }
