"""initial

Revision ID: 0001
Revises: 
Create Date: 2026-10-03 01:00:00.000000

"""
from alembic import op
from app.db.base import Base
import app.models  # noqa: F401 — register all declarative models

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
