"""Add transfer snapshots and simulated invoice settlement fields."""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column, type_ in [
        ('language_mix', sa.JSON()), ('infrastructure', sa.JSON()),
        ('staffing_level', sa.Integer()), ('security_requirements', sa.JSON()),
        ('product_version', sa.String()), ('simulated', sa.Boolean()),
    ]:
        op.add_column('district_profiles', sa.Column(column, type_, nullable=False,
            server_default=sa.text("'{}'" if column == 'language_mix' else ("'[]'" if column in {'infrastructure','security_requirements'} else ('0' if column in {'staffing_level','simulated'} else "'unknown'")))))
    for column, type_, default in [
        ('technical_suitability', sa.String(), "'Not demonstrated'"),
        ('procurement_route_status', sa.String(), "'Not assessed'"),
        ('source_snapshot', sa.JSON(), "'{}'"), ('receiving_snapshot', sa.JSON(), "'{}'"),
        ('created_milestone_ids', sa.JSON(), "'[]'"),
    ]:
        op.add_column('transfer_assessments', sa.Column(column, type_, nullable=False, server_default=sa.text(default)))
    op.add_column('invoices', sa.Column('storage_path', sa.String(), nullable=True))
    op.add_column('invoices', sa.Column('content_sha256', sa.String(length=64), nullable=True))
    op.add_column('invoices', sa.Column('approval_status', sa.String(), nullable=False, server_default='Submitted'))
    op.add_column('invoices', sa.Column('approved_by', sa.UUID(), nullable=True))
    op.add_column('invoices', sa.Column('approved_at', sa.DateTime(), nullable=True))
    op.add_column('payment_records', sa.Column('reference', sa.String(), nullable=True))
    op.add_column('payment_records', sa.Column('simulated', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('payment_records', sa.Column('details', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column('payment_attempts', sa.Column('reference', sa.String(length=100), nullable=True))
    op.add_column('payment_attempts', sa.Column('simulated', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    for table, columns in {
        'payment_attempts': ['simulated', 'reference'],
        'payment_records': ['details', 'simulated', 'reference'],
        'invoices': ['approved_at', 'approved_by', 'approval_status', 'content_sha256', 'storage_path'],
        'transfer_assessments': ['created_milestone_ids', 'receiving_snapshot', 'source_snapshot', 'procurement_route_status', 'technical_suitability'],
        'district_profiles': ['simulated', 'product_version', 'security_requirements', 'staffing_level', 'infrastructure', 'language_mix'],
    }.items():
        for column in columns:
            op.drop_column(table, column)
