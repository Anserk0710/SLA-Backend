from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.constants import NOTIFICATION_TYPE_TICKET, RoleName, TicketStatus
from app.models.ticket import Ticket
from app.models.ticket_assignment import TicketAssignment
from app.models.ticket_checkin import TicketCheckIn
from app.models.ticket_resolution import TicketResolution
from app.models.ticket_status_log import TicketStatusLog
from app.models.user import User
from app.services.notification_service import create_notifications_for_roles
from app.services.sla_service import refresh_ticket_sla_state
from app.services.ticket_service import get_public_status_from_internal


def _ensure_ticket_assigned_to_technician(db: Session, ticket_id: str, technician_user_id: str) -> Ticket:
    stmt = (
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(
            selectinload(Ticket.assignments),
            selectinload(Ticket.checkins),
            selectinload(Ticket.resolution),
        )
    )
    ticket = db.scalar(stmt)

    if ticket is None:
        raise ValueError("Ticket tidak ditemukan")

    assigned = any(
        assignment.technician_user_id == technician_user_id
        for assignment in ticket.assignments
    )

    if not assigned:
        raise ValueError("Ticket ini tidak di-assign ke Anda")

    return ticket


def _create_status_log(
    db: Session,
    ticket_id: str,
    old_status: str | None,
    new_status: str,
    notes: str | None,
    changed_by_user_id: str | None,
) -> None:
    db.add(
        TicketStatusLog(
            ticket_id=ticket_id,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
            changed_by_user_id=changed_by_user_id,
        )
    )


def list_assigned_tickets(db: Session, current_user: User) -> list[dict]:
    stmt = (
        select(Ticket)
        .join(TicketAssignment, TicketAssignment.ticket_id == Ticket.id)
        .where(
            TicketAssignment.technician_user_id == current_user.id,
            Ticket.internal_status.in_(
                [
                    TicketStatus.ASSIGNED.value,
                    TicketStatus.ON_SITE.value,
                    TicketStatus.IN_PROGRESS.value,
                    TicketStatus.RESOLVED.value,
                ]
            ),
        )
        .options(
            selectinload(Ticket.checkins),
            selectinload(Ticket.resolution),
        )
        .order_by(Ticket.created_at.desc())
    )

    tickets = db.scalars(stmt).unique().all()

    result: list[dict] = []
    for ticket in tickets:
        refresh_ticket_sla_state(ticket)

        checkin = next(
            (item for item in ticket.checkins if item.technician_user_id == current_user.id),
            None,
        )
        resolution = next(
            (item for item in ticket.resolution if item.technician_user_id == current_user.id),
            None,
        )

        result.append(
            {
                "id": ticket.id,
                "ticket_code": ticket.ticket_code,
                "full_name": ticket.full_name,
                "category": ticket.category,
                "pic_name": ticket.pic_name,
                "phone_number": ticket.phone_number,
                "internal_status": ticket.internal_status,
                "public_status": ticket.public_status,
                "sla_deadline": ticket.sla_deadline,
                "is_sla_breached": ticket.is_sla_breached,
                "created_at": ticket.created_at,
                "has_checkin": checkin is not None,
                "has_resolution": resolution is not None,
            }
        )

    return result


def get_assigned_ticket_detail(db: Session, ticket_id: str, current_user: User) -> dict:
    ticket = _ensure_ticket_assigned_to_technician(db, ticket_id, current_user.id)
    refresh_ticket_sla_state(ticket)

    checkin = next(
        (item for item in ticket.checkins if item.technician_user_id == current_user.id),
        None,
    )
    resolution = next(
        (item for item in ticket.resolution if item.technician_user_id == current_user.id),
        None,
    )

    return {
        "id": ticket.id,
        "ticket_code": ticket.ticket_code,
        "full_name": ticket.full_name,
        "full_address": ticket.full_address,
        "category": ticket.category,
        "description": ticket.description,
        "pic_name": ticket.pic_name,
        "phone_number": ticket.phone_number,
        "internal_status": ticket.internal_status,
        "public_status": ticket.public_status,
        "sla_deadline": ticket.sla_deadline,
        "is_sla_breached": ticket.is_sla_breached,
        "created_at": ticket.created_at,
        "checkin": (
            {
                "id": checkin.id,
                "photo_secure_url": checkin.photo_secure_url,
                "photo_format": checkin.photo_format,
                "photo_bytes": checkin.photo_bytes,
                "latitude": checkin.latitude,
                "longitude": checkin.longitude,
                "address": checkin.address,
                "notes": checkin.notes,
                "server_timestamp": checkin.server_timestamp,
            }
            if checkin
            else None
        ),
        "resolution": (
            {
                "id": resolution.id,
                "video_secure_url": resolution.video_secure_url,
                "video_format": resolution.video_format,
                "video_bytes": resolution.video_bytes,
                "video_duration": float(resolution.video_duration) if resolution.video_duration is not None else None,
                "latitude": resolution.latitude,
                "longitude": resolution.longitude,
                "address": resolution.address,
                "resolution_note": resolution.resolution_note,
                "server_timestamp": resolution.server_timestamp,
            }
            if resolution
            else None
        ),
    }


def submit_checkin(
    db: Session,
    *,
    ticket_id: str,
    current_user: User,
    latitude: float,
    longitude: float,
    address: str,
    notes: str | None,
    upload_result: dict,
    original_filename: str | None,
) -> dict:
    ticket = _ensure_ticket_assigned_to_technician(db, ticket_id, current_user.id)

    existing_checkin = next(
        (item for item in ticket.checkins if item.technician_user_id == current_user.id),
        None,
    )
    if existing_checkin:
        raise ValueError("Anda sudah pernah check-in untuk ticket ini")

    if ticket.internal_status not in {
        TicketStatus.ASSIGNED.value,
        TicketStatus.ON_SITE.value,
        TicketStatus.IN_PROGRESS.value,
    }:
        raise ValueError("Status ticket tidak valid untuk check-in")

    server_timestamp = datetime.now(timezone.utc)

    checkin = TicketCheckIn(
        ticket_id=ticket.id,
        technician_user_id=current_user.id,
        photo_public_id=upload_result.get("public_id"),
        photo_secure_url=upload_result.get("secure_url"),
        photo_resource_type=upload_result.get("resource_type", "image"),
        photo_format=upload_result.get("format"),
        photo_bytes=upload_result.get("bytes", 0),
        photo_width=upload_result.get("width"),
        photo_height=upload_result.get("height"),
        original_filename=original_filename,
        latitude=latitude,
        longitude=longitude,
        address=address.strip(),
        notes=notes.strip() if notes else None,
        server_timestamp=server_timestamp,
    )
    db.add(checkin)

    old_status = ticket.internal_status
    if ticket.internal_status == TicketStatus.ASSIGNED.value:
        new_status = TicketStatus.ON_SITE.value
        ticket.internal_status = new_status
        ticket.public_status = get_public_status_from_internal(new_status)

        _create_status_log(
            db,
            ticket_id=ticket.id,
            old_status=old_status,
            new_status=new_status,
            notes=f"Technician check-in oleh {current_user.full_name}",
            changed_by_user_id=current_user.id,
        )

    db.commit()
    db.refresh(ticket)

    return {
        "message": "Check-in berhasil disimpan",
        "internal_status": ticket.internal_status,
        "public_status": ticket.public_status,
    }


def submit_resolution(
    db: Session,
    *,
    ticket_id: str,
    current_user: User,
    latitude: float,
    longitude: float,
    address: str,
    resolution_note: str,
    upload_result: dict,
    original_filename: str | None,
) -> dict:
    ticket = _ensure_ticket_assigned_to_technician(db, ticket_id, current_user.id)

    existing_checkin = next(
        (item for item in ticket.checkins if item.technician_user_id == current_user.id),
        None,
    )
    if existing_checkin is None:
        raise ValueError("Anda harus check-in terlebih dahulu sebelum submit selesai")

    existing_resolution = next(
        (item for item in ticket.resolution if item.technician_user_id == current_user.id),
        None,
    )
    if existing_resolution:
        raise ValueError("Anda sudah pernah submit selesai untuk ticket ini")

    if ticket.internal_status not in {
        TicketStatus.ON_SITE.value,
        TicketStatus.IN_PROGRESS.value,
        TicketStatus.ASSIGNED.value,
    }:
        raise ValueError("Status ticket tidak valid untuk submit selesai")

    server_timestamp = datetime.now(timezone.utc)

    resolution = TicketResolution(
        ticket_id=ticket.id,
        technician_user_id=current_user.id,
        video_public_id=upload_result.get("public_id"),
        video_secure_url=upload_result.get("secure_url"),
        video_resource_type=upload_result.get("resource_type", "video"),
        video_format=upload_result.get("format"),
        video_bytes=upload_result.get("bytes", 0),
        video_width=upload_result.get("width"),
        video_height=upload_result.get("height"),
        video_duration=upload_result.get("duration"),
        original_filename=original_filename,
        latitude=latitude,
        longitude=longitude,
        address=address.strip(),
        resolution_note=resolution_note.strip(),
        server_timestamp=server_timestamp,
    )
    db.add(resolution)

    old_status = ticket.internal_status
    new_status = TicketStatus.RESOLVED.value
    ticket.internal_status = new_status
    ticket.public_status = get_public_status_from_internal(new_status)

    _create_status_log(
        db,
        ticket_id=ticket.id,
        old_status=old_status,
        new_status=new_status,
        notes=f"Ticket diselesaikan oleh {current_user.full_name}: {resolution_note.strip()}",
        changed_by_user_id=current_user.id,
    )

    db.commit()
    db.refresh(ticket)

    create_notifications_for_roles(
        db=db,
        role_names=[RoleName.ADMIN.value, RoleName.HEAD.value],
        title="Ticket selesai dikerjakan",
        message=f"Ticket {ticket.ticket_code} telah diselesaikan teknisi.",
        notification_type=NOTIFICATION_TYPE_TICKET,
        ticket_id=ticket.id,
    )

    return {
        "message": "Bukti selesai berhasil disimpan",
        "internal_status": ticket.internal_status,
        "public_status": ticket.public_status,
    }
