from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, text, func, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.db.base import Base

class DistrictProfile(Base):
    __tablename__ = 'district_profiles'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    name: Mapped[str] = mapped_column(String)
    district_type: Mapped[str] = mapped_column(String)
    daily_case_volume: Mapped[int] = mapped_column(Integer)
    bandwidth_mbps: Mapped[float] = mapped_column(Float)
    primary_language: Mapped[str] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    language_mix: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    infrastructure: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    staffing_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    security_requirements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    product_version: Mapped[str] = mapped_column(String, default='unknown', nullable=False)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class TransferAssessment(Base):
    __tablename__ = 'transfer_assessments'
    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agreement_id: Mapped[str] = mapped_column(String, ForeignKey('pilot_agreements.id'))
    receiving_district_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('district_profiles.id'))
    assessed_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    status: Mapped[str] = mapped_column(String)
    findings: Mapped[list] = mapped_column(JSON)
    procurement_note: Mapped[str] = mapped_column(String)
    assessed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    technical_suitability: Mapped[str] = mapped_column(String, default='Not demonstrated', nullable=False)
    procurement_route_status: Mapped[str] = mapped_column(String, default='Not assessed', nullable=False)
    source_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    receiving_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_milestone_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
