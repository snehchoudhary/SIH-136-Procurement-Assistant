from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base


class Role(Base):
    __tablename__ = 'roles'
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String(40), ForeignKey('roles.name'), nullable=False)
    organisation_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey('organisations.id'), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
