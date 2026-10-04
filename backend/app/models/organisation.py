from sqlalchemy import Column, String, DateTime, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class Organisation(Base):
    __tablename__ = 'organisations'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String)
    org_type: Mapped[str] = mapped_column(String)
    district: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# Keep the existing British-spelling import compatible while exposing the
# requested Organization model name to new code.
Organization = Organisation
