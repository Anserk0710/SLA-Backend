from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

class RoleRead(BaseModel):
    id: UUID
    name: str

    model_config = ConfigDict(from_attributes=True)

class UserRead(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    is_active: bool
    role: RoleRead

    model_config = ConfigDict(from_attributes=True)
