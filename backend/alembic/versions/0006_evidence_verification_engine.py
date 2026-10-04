"""Persist reproducible evidence engine results and correction threads.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def _add(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if table in inspector.get_table_names() and column.name not in {c['name'] for c in inspector.get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add('evidence_versions2', sa.Column('metric_definition_hash', sa.String(64), nullable=False, server_default=''))
    _add('evidence_versions2', sa.Column('measurement_plan_snapshot', sa.JSON(), nullable=False, server_default='{}'))
    _add('kpi_results2', sa.Column('python_code', sa.String(), nullable=False, server_default=''))
    _add('kpi_results2', sa.Column('is_stale', sa.Boolean(), nullable=False, server_default=sa.false()))
    if 'evidence_review_threads' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            'evidence_review_threads',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('upload_id', sa.String(36), sa.ForeignKey('evidence_uploads.id'), nullable=False),
            sa.Column('agreement_id', sa.String(), sa.ForeignKey('pilot_agreements.id'), nullable=False),
            sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('subject', sa.String(), nullable=False),
            sa.Column('initial_message', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False, server_default='open'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    if 'evidence_review_threads' in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table('evidence_review_threads')
    for table, columns in {
        'kpi_results2': ('is_stale', 'python_code'),
        'evidence_versions2': ('measurement_plan_snapshot', 'metric_definition_hash'),
    }.items():
        present = {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for column in columns:
            if column in present:
                op.drop_column(table, column)
