from datetime import date
from typing import Optional

from pydantic import BaseModel

class ReportFilterSchema(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    date_form: Optional[date] = None
    date_to: Optional[date] = None
    technician_id: Optional[str] = None