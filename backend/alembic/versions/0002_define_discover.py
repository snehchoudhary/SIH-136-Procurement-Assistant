"""Add structured challenge plans and startup capability evidence.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def _add_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if table in inspector.get_table_names() and column.name not in {item['name'] for item in inspector.get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add_if_missing('challenges', sa.Column('measurement_locked', sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_if_missing('challenge_versions', sa.Column('problem_statement', sa.String(), nullable=False, server_default=''))
    _add_if_missing('challenge_versions', sa.Column('outcomes', sa.JSON(), nullable=False, server_default='[]'))
    _add_if_missing('challenge_versions', sa.Column('baseline', sa.String(), nullable=False, server_default='Baseline unavailable'))
    _add_if_missing('challenge_versions', sa.Column('test_plan', sa.String(), nullable=False, server_default=''))
    _add_if_missing('challenge_versions', sa.Column('test_duration_days', sa.Integer(), nullable=True))
    _add_if_missing('challenge_versions', sa.Column('acceptance_criteria', sa.JSON(), nullable=False, server_default='[]'))
    _add_if_missing('challenge_versions', sa.Column('input_language', sa.String(), nullable=False, server_default='en'))
    _add_if_missing('challenge_versions', sa.Column('change_note', sa.String(), nullable=False, server_default='Initial version'))
    _add_if_missing('challenge_versions', sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_if_missing('startups', sa.Column('capability_tags', sa.JSON(), nullable=False, server_default='[]'))
    _add_if_missing('startups', sa.Column('domain_experience', sa.String(), nullable=False, server_default='Not documented'))
    _add_if_missing('startups', sa.Column('languages_supported', sa.JSON(), nullable=False, server_default='[]'))
    _add_if_missing('startups', sa.Column('deployment_readiness', sa.String(), nullable=False, server_default='Not documented'))
    _add_if_missing('startups', sa.Column('evidence_snippets', sa.JSON(), nullable=False, server_default='[]'))

    inspector = sa.inspect(op.get_bind())
    columns = {item['name']: item for item in inspector.get_columns('challenge_versions')}
    for name, type_ in (('budget', sa.Integer()), ('target_pct', sa.Float()), ('deadline', sa.Date())):
        if name in columns and not columns[name]['nullable']:
            op.alter_column('challenge_versions', name, existing_type=type_, nullable=True)


def downgrade() -> None:
    # These fields are data-bearing additions and are intentionally retained on downgrade.
    pass
