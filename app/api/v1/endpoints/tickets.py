from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.constants import RoleName
from app.models.user import User
from app.schemas.admin_ticket import (
    ActionMessageResponse,
    TicketAssginRequest,
    TicketDetailResponse,
    TicketListItemResponse,
    TicketRespondRequest,
)
from app.services.admin_ticket_service import (
    assign_ticket_technicians,
    get_ticket_detail,
    list_tickets,
    respond_ticket
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("", response_model=list[TicketListItemResponse])
def get_ticket_list(
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)
    ),
):
    return list_tickets(db=db, status=status_filter, q=q)

@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket_detail_by_id(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)
    )
):
    ticket = get_ticket_detail(db=db, ticket_id=ticket_id)

    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket tidak ditemukan")
    
    return ticket

@router.post(
    "/{ticket_id}/respond", response_model=ActionMessageResponse, status_code=status.HTTP_200_OK
)
def respond_ticket_endpoint(
    ticket_id: str,
    payload: TicketRespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)
    ),
):
    try:
        respond_ticket(
            db=db,
            ticket_id=ticket_id,
            response_note=payload.response_note,
            current_user=current_user,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Ticket tidak ditemukan":
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": "Respon Ticket Berhasil Disimpan"}

@router.post(
    "/{ticket_id}/assign",
    response_model=ActionMessageResponse,
    status_code=status.HTTP_200_OK,
)
def assign_ticket_endpoint(
    ticket_id: str,
    payload: TicketAssginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)
    ),
):
    try:
        assign_ticket_technicians(
            db=db,
            ticket_id=ticket_id,
            technician_user_ids=payload.technician_user_ids,
            current_user=current_user,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Ticket tidak ditemukan":
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": "Assign Technician Berhasil Disimpan"}
