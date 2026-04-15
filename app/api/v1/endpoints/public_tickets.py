from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.constants import NOTIFICATION_TYPE_TICKET, RoleName
from app.schemas.ticket import (
    PublicTicketCreate,
    PublicTicketCreateResponse,
    PublicTicketTrackingResponse,
)
from app.services.notification_service import create_notifications_for_roles
from app.services.ticket_service import create_public_ticket, track_public_ticket

router = APIRouter(prefix="/public", tags=["public tickets"])


@router.post("/tickets", response_model=PublicTicketCreateResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: PublicTicketCreate,
    db: Session = Depends(get_db),
):
    ticket = create_public_ticket(db, payload)
    create_notifications_for_roles(
        db=db,
        role_names=[RoleName.ADMIN.value, RoleName.HEAD.value],
        title="Ticket baru masuk",
        message=f"Ticket {ticket.ticket_code} baru dibuat oleh client.",
        notification_type=NOTIFICATION_TYPE_TICKET,
        ticket_id=ticket.id,
    )

    return {
        "ticket_code": ticket.ticket_code,
        "public_status": ticket.public_status,
        "message": "Ticket berhasil dibuat",
    }


@router.get("/tracking", response_model=PublicTicketTrackingResponse)
def tracking_ticket(
    ticket_code: str = Query(..., min_length=5, max_length=50),
    phone_number: str = Query(..., min_length=8, max_length=30),
    db: Session = Depends(get_db),
):
    ticket = track_public_ticket(
        db=db,
        ticket_code=ticket_code,
        phone_number=phone_number,
    )

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket tidak ditemukan. Periksa ticket code dan nomor HP.",
        )

    return ticket
