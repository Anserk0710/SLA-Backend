from datetime import datetime

from pydantic import BaseModel, Field, field_validator

class TechnicianOption(BaseModel):
    id: str
    full_name: str
    email: str

class AssignedTechnicianRead(BaseModel):
    id: str
    full_name: str
    email: str

class TicketStatusLogRead(BaseModel):
    id: str
    old_status: str | None
    new_status: str
    notes: str | None
    changed_by_name: str | None
    created_at: datetime

class DashboardSummaryResponse(BaseModel):
    total_tickets: int
    belum_direspon: int
    sudah_direspon: int
    on_progress: int
    selesai: int

class TicketListItemResponse(BaseModel):
    id: str
    ticket_code: str
    full_name: str
    category: str
    pic_name: str
    phone_number: str
    internal_status: str
    public_status: str
    created_at: datetime
    assigned_technicians: list[AssignedTechnicianRead] = []

class TicketDetailResponse(TicketListItemResponse):
    full_address: str
    description: str
    inital_respons: str | None = None
    responded_at: datetime | None = None
    responded_by_name: str | None = None
    status_logs: list[TicketStatusLogRead] = []

class TicketRespondRequest(BaseModel):
    response_note: str = Field(..., min_length=10, max_length=2000)
    @field_validator("response_note")
    @classmethod
    def validate_response_note(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Catatan tidak boleh kosong")
        return value
    
class TicketAssginRequest(BaseModel):
    technician_user_ids: list[str] = Field(..., min_length=1)
    @field_validator("technician_user_ids")
    @classmethod
    def validate_unique_ids(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for item in value:
            cleaned = item.strip()
            if not cleaned:
                continue
            if cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)

        if not result:
            raise ValueError("Tidak ada teknisi yang dipilih")
        
        return result
    
class ActionMessageResponse(BaseModel):
    message: str
