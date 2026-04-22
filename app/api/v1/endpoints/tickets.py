from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.core.constants import RoleName
from app.core.permissions import (
    ensure_assign_permission,
    ensure_ticket_visible_to_user,
    require_roles,
)
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
    respond_ticket,
    serialize_ticket_list_item,
)
from app.services.ticket_service import get_ticket_list as get_filtered_ticket_list

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("", response_model=list[TicketListItemResponse])
def list_tickets_endpoint(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    technician_id: str | None = Query(default=None),
    q: str | None = Query(None),
    skip: int = Query(default=0),
    limit: int = Query(default=20),
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(RoleName.ADMIN.value, RoleName.HEAD.value)
    ),
):
    tickets = get_filtered_ticket_list(
        db=db,
        status=status_filter,
        category=category,
        date_from=date_from,
        date_to=date_to,
        technician_id=technician_id,
        q=q,
        skip=skip,
        limit=limit,
    )
    return [serialize_ticket_list_item(ticket) for ticket in tickets]


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

    ensure_ticket_visible_to_user(db=db, ticket_id=ticket_id, current_user=current_user)

    return ticket

@router.post(
    "/{ticket_id}/respond",
    response_model=ActionMessageResponse,
    status_code=http_status.HTTP_200_OK,
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
    status_code=http_status.HTTP_200_OK,
)
def assign_ticket_endpoint(
    ticket_id: str,
    payload: TicketAssginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    ensure_assign_permission(current_user)

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
