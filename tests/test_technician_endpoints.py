from datetime import datetime, timezone
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.endpoints import technician as technician_endpoint_module
from app.core.config import settings
from app.core.constants import RoleName, TicketStatus
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.ticket_checkin import TicketCheckIn
from app.models.ticket_resolution import TicketResolution
from app.models.user import User


def _get_or_create_role(db_session: Session, role_name: RoleName) -> Role:
    role = db_session.scalar(select(Role).where(Role.name == role_name.value))
    if role is not None:
        return role

    role = Role(name=role_name.value)
    db_session.add(role)
    db_session.flush()
    return role


def test_check_in_endpoint_saves_metadata_and_returns_file_url(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    technician_role = _get_or_create_role(db_session, RoleName.TECHNICIAN)
    technician = User(
        full_name="Teknisi Endpoint",
        email="teknisi.endpoint@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-ENDPOINT-001",
        full_name="Budi Endpoint",
        full_address="Jl. Endpoint No. 1",
        category="Internet",
        description="Uji check-in endpoint.",
        pic_name="PIC Endpoint",
        phone_number="081200000901",
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

    async def fake_upload_checkin_photo(_file):
        return {
            "public_id": "uploads/checkins/2026/04/17/arrival.jpg",
            "secure_url": "https://ptcahyaintanmedika.co.id/uploads/checkins/2026/04/17/arrival.jpg",
            "resource_type": "image",
            "format": "jpg",
            "bytes": 12345,
            "width": None,
            "height": None,
            "duration": None,
            "disk_path": "D:/uploads/checkins/2026/04/17/arrival.jpg",
        }

    monkeypatch.setattr(
        technician_endpoint_module,
        "upload_checkin_photo",
        fake_upload_checkin_photo,
    )

    client.app.dependency_overrides[get_current_user] = lambda: technician
    try:
        response = client.post(
            f"{settings.API_V1_PREFIX}/technician/tickets/{ticket.id}/check-in",
            data={
                "latitude": "-6.2",
                "longitude": "106.8",
                "address": "Jl. Endpoint No. 1",
                "notes": "Sudah tiba di lokasi",
            },
            files={
                "photo": ("arrival.jpg", BytesIO(b"fake-image-content"), "image/jpeg"),
            },
        )
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Check-in berhasil disimpan",
        "internal_status": TicketStatus.ON_SITE.value,
        "public_status": "Sedang Dikerjakan",
        "file_url": "https://ptcahyaintanmedika.co.id/uploads/checkins/2026/04/17/arrival.jpg",
    }

    checkin = db_session.scalar(
        select(TicketCheckIn).where(TicketCheckIn.ticket_id == ticket.id)
    )
    assert checkin is not None
    assert checkin.photo_public_id == "uploads/checkins/2026/04/17/arrival.jpg"
    assert (
        checkin.photo_secure_url
        == "https://ptcahyaintanmedika.co.id/uploads/checkins/2026/04/17/arrival.jpg"
    )
    assert checkin.photo_format == "jpg"
    assert checkin.photo_bytes == 12345
    assert checkin.original_filename == "arrival.jpg"


def test_resolve_endpoint_saves_metadata_and_returns_file_url(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    technician_role = _get_or_create_role(db_session, RoleName.TECHNICIAN)
    technician = User(
        full_name="Teknisi Resolve",
        email="teknisi.resolve.endpoint@example.com",
        hashed_password="hashed-password",
        is_active=True,
        role_id=technician_role.id,
    )
    ticket = Ticket(
        ticket_code="TCK-ENDPOINT-002",
        full_name="Sari Endpoint",
        full_address="Jl. Endpoint No. 2",
        category="CCTV",
        description="Uji resolve endpoint.",
        pic_name="PIC Resolve",
        phone_number="081200000902",
        internal_status=TicketStatus.ON_SITE.value,
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
    db_session.add(
        TicketCheckIn(
            ticket_id=ticket.id,
            technician_user_id=technician.id,
            photo_public_id="uploads/checkins/2026/04/17/existing.jpg",
            photo_secure_url="https://ptcahyaintanmedika.co.id/uploads/checkins/2026/04/17/existing.jpg",
            photo_resource_type="image",
            photo_format="jpg",
            photo_bytes=111,
            photo_width=None,
            photo_height=None,
            original_filename="existing.jpg",
            latitude=-6.2,
            longitude=106.8,
            address="Jl. Endpoint No. 2",
            notes="Sudah tiba",
            server_timestamp=datetime(2026, 4, 17, 10, 0, 0, tzinfo=timezone.utc),
        )
    )
    db_session.commit()

    async def fake_upload_resolution_video(_file):
        return {
            "public_id": "uploads/resolutions/2026/04/17/resolution.mp4",
            "secure_url": "https://ptcahyaintanmedika.co.id/uploads/resolutions/2026/04/17/resolution.mp4",
            "resource_type": "video",
            "format": "mp4",
            "bytes": 45678,
            "width": None,
            "height": None,
            "duration": None,
            "disk_path": "D:/uploads/resolutions/2026/04/17/resolution.mp4",
        }

    monkeypatch.setattr(
        technician_endpoint_module,
        "upload_resolution_video",
        fake_upload_resolution_video,
    )

    client.app.dependency_overrides[get_current_user] = lambda: technician
    try:
        response = client.post(
            f"{settings.API_V1_PREFIX}/technician/tickets/{ticket.id}/resolve",
            data={
                "latitude": "-6.2",
                "longitude": "106.8",
                "address": "Jl. Endpoint No. 2",
                "resolution_note": "Masalah sudah selesai.",
            },
            files={
                "video": ("resolution.mp4", BytesIO(b"fake-video-content"), "video/mp4"),
            },
        )
    finally:
        client.app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Bukti selesai berhasil disimpan",
        "internal_status": TicketStatus.RESOLVED.value,
        "public_status": "Sudah Selesai",
        "file_url": "https://ptcahyaintanmedika.co.id/uploads/resolutions/2026/04/17/resolution.mp4",
    }

    resolution = db_session.scalar(
        select(TicketResolution).where(TicketResolution.ticket_id == ticket.id)
    )
    assert resolution is not None
    assert resolution.video_public_id == "uploads/resolutions/2026/04/17/resolution.mp4"
    assert (
        resolution.video_secure_url
        == "https://ptcahyaintanmedika.co.id/uploads/resolutions/2026/04/17/resolution.mp4"
    )
    assert resolution.video_format == "mp4"
    assert resolution.video_bytes == 45678
    assert resolution.original_filename == "resolution.mp4"
