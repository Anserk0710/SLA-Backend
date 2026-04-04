from uuid import uuid4

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class TicketAssignment(Base):
    __tablename__ = "ticket_assignments"
    __table_args__ = (
        UniqueConstraint("ticket_id", "technician_user_id", name="uq_ticket_technician"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    technician_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    assigned_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="assignments")
    technician = relationship("User", foreign_keys=[technician_user_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
