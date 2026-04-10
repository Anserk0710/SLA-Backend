from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.config import settings
from app.core.constants import RoleName
from app.models.user import User
from app.schemas.technician import (
    TechnicianActionResponse,
    TechnicianAssignedTicketResponse,
    TechnicianReverseGeocodeResponse,
    TechnicianTicketDetailResponse,
)
from app.services.cloudinary_service import upload_checkin_photo, upload_resolution_video
from app.services.location_service import reverse_geocode_location
from app.services.technician_service import (
    get_assigned_ticket_detail,
    list_assigned_tickets,
    submit_checkin,
    submit_resolution,
)
from app.utils.file_upload import validate_image_file, validate_video_file

router = APIRouter(prefix="/technician", tags=["technician"])


@router.get("/location/reverse-geocode", response_model=TechnicianReverseGeocodeResponse)
def reverse_geocode_current_location(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(require_roles(RoleName.TECHNICIAN.value)),
):
    try:
        return reverse_geocode_location(latitude, longitude)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/tickets/assigned", response_model=list[TechnicianAssignedTicketResponse])
def get_my_assigned_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TECHNICIAN.value)),
):
    return list_assigned_tickets(db, current_user)


@router.get("/tickets/{ticket_id}", response_model=TechnicianTicketDetailResponse)
def get_my_ticket_detail(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TECHNICIAN.value)),
):
    try:
        return get_assigned_ticket_detail(db, ticket_id, current_user)
    except ValueError as exc:
        message = str(exc)
        if message == "Ticket tidak ditemukan":
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=403, detail=message)


@router.post("/tickets/{ticket_id}/check-in", response_model=TechnicianActionResponse)
def check_in_ticket(
    ticket_id: str,
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    notes: str | None = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TECHNICIAN.value)),
):
    validate_image_file(photo, settings.MAX_IMAGE_UPLOAD_MB)

    try:
        upload_result = upload_checkin_photo(photo.file, filename=photo.filename)
        return submit_checkin(
            db=db,
            ticket_id=ticket_id,
            current_user=current_user,
            latitude=latitude,
            longitude=longitude,
            address=address,
            notes=notes,
            upload_result=upload_result,
            original_filename=photo.filename,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Ticket tidak ditemukan":
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)


@router.post("/tickets/{ticket_id}/resolve", response_model=TechnicianActionResponse)
def resolve_ticket(
    ticket_id: str,
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    resolution_note: str = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleName.TECHNICIAN.value)),
):
    validate_video_file(video, settings.MAX_VIDEO_UPLOAD_MB)

    try:
        upload_result = upload_resolution_video(video.file, filename=video.filename)
        return submit_resolution(
            db=db,
            ticket_id=ticket_id,
            current_user=current_user,
            latitude=latitude,
            longitude=longitude,
            address=address,
            resolution_note=resolution_note,
            upload_result=upload_result,
            original_filename=video.filename,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Ticket tidak ditemukan":
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=400, detail=message)
