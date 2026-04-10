from datetime import datetime

from pydantic import BaseModel, Field


class TechnicianAssignedTicketResponse(BaseModel):
    id: str
    ticket_code: str
    full_name: str
    category: str
    pic_name: str
    phone_number: str
    internal_status: str
    public_status: str
    created_at: datetime
    has_checkin: bool
    has_resolution: bool


class TechnicianCheckInRead(BaseModel):
    id: str
    photo_secure_url: str
    photo_format: str | None = None
    photo_bytes: int
    latitude: float
    longitude: float
    address: str
    notes: str | None = None
    server_timestamp: datetime


class TechnicianResolutionRead(BaseModel):
    id: str
    video_secure_url: str
    video_format: str | None = None
    video_bytes: int
    video_duration: float | None = None
    latitude: float
    longitude: float
    address: str
    resolution_note: str
    server_timestamp: datetime


class TechnicianTicketDetailResponse(BaseModel):
    id: str
    ticket_code: str
    full_name: str
    full_address: str
    category: str
    description: str
    pic_name: str
    phone_number: str
    internal_status: str
    public_status: str
    created_at: datetime
    checkin: TechnicianCheckInRead | None = None
    resolution: TechnicianResolutionRead | None = None


class TechnicianActionResponse(BaseModel):
    message: str
    internal_status: str
    public_status: str


class TechnicianReverseGeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    full_address: str


class ResolutionFormData(BaseModel):
    resolution_note: str = Field(..., min_length=3, max_length=2000)
