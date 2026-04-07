from uuid import uuid4
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, func, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

class TicketResolution(Base):
    __tablename__ = "ticket_resolution"
    __table_args__= (
        UniqueConstraint("ticket_id", "technician_user_id", name="uq_ticket_resolution_ticket_technician"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()), index=True)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    technician_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)

    video_public_id: Mapped[str] = mapped_column(String(255))
    video_secure_url: Mapped[str] = mapped_column(Text)
    video_resource_type: Mapped[str] = mapped_column(String(50), default="video")
    video_format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    video_bytes: Mapped[int] = mapped_column(Integer)
    video_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_duration: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    address: Mapped[str] = mapped_column(Text)
    resolution_note: Mapped[str] = mapped_column(Text)

    server_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    ticket = relationship("Ticket", back_populates="resolution")
    technician = relationship("User", foreign_keys=[technician_user_id])