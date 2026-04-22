from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.utils.phone import normalize_phone_number

class PublicTicketCreate(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=150)
    full_address: str = Field(..., min_length=10, max_length=255)
    category: str = Field(..., min_length=3, max_length=50)
    item_name: str = Field(..., min_length=3, max_length=150)
    description: str = Field(..., min_length=10, max_length=2000)
    pic_name: str = Field(..., min_length=3, max_length=150)
    phone_number: str = Field(..., min_length=8, max_length=30)

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized = normalize_phone_number(value.strip())

        if len(normalized) < 8 or len(normalized) > 20:
            raise ValueError("Nomor telepon tidak valid setelah dinormalisasi.")

        return normalized
    
class PublicTicketCreateResponse(BaseModel):
    ticket_code: str
    public_status: str
    message: str

PublicTicketResponse = PublicTicketCreateResponse

class PublicTicketTrackingResponse(BaseModel):
    ticket_code: str
    full_name: str
    category: str
    item_name: str
    public_status: str
    internal_status: str
    sla_deadline: datetime | None = None
    is_sla_breached: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
