"""Persist documents submitted for simulated adapter manual verification.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if 'manual_verification_uploads' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'manual_verification_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('startup_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_adapter', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='Pending human verification'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['startup_id'], ['startups.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.alter_column('manual_verification_uploads', 'status', server_default=None)


def downgrade() -> None:
    op.drop_table('manual_verification_uploads')
