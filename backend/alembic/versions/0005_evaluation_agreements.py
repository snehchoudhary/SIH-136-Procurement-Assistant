"""Add versioned agreements, milestone plans, committee decisions, and questions.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if table in inspector.get_table_names() and column.name not in {item['name'] for item in inspector.get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    _add_column_if_missing('rubric_versions', sa.Column('criteria', sa.JSON(), nullable=False, server_default='[]'))
    _add_column_if_missing('evaluations', sa.Column('submitted', sa.Boolean(), nullable=False, server_default=sa.true()))

    if 'pilot_agreements' in inspector.get_table_names():
        approved_column = next((column for column in inspector.get_columns('pilot_agreements') if column['name'] == 'approved_by'), None)
        if approved_column and not approved_column['nullable']:
            op.alter_column('pilot_agreements', 'approved_by', existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    _add_column_if_missing('pilot_agreements', sa.Column('terms_accepted', sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing('pilot_agreements', sa.Column('approval_chain', sa.JSON(), nullable=False, server_default='[]'))
    _add_column_if_missing('pilot_agreements', sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True))

    _add_column_if_missing('agreement_versions', sa.Column('template_key', sa.String(), nullable=False, server_default='standard-pilot'))
    _add_column_if_missing('agreement_versions', sa.Column('template_version', sa.Integer(), nullable=False, server_default='1'))
    _add_column_if_missing('agreement_versions', sa.Column('clauses', sa.JSON(), nullable=False, server_default='{}'))
    _add_column_if_missing('agreement_versions', sa.Column('change_note', sa.String(), nullable=False, server_default='Initial agreement draft'))
    _add_column_if_missing('agreement_versions', sa.Column('approved', sa.Boolean(), nullable=False, server_default=sa.false()))

    _add_column_if_missing('milestones', sa.Column('evidence_requirements', sa.JSON(), nullable=False, server_default='[]'))
    _add_column_if_missing('milestones', sa.Column('acceptance_criteria', sa.JSON(), nullable=False, server_default='[]'))
    _add_column_if_missing('milestones', sa.Column('linked_kpis', sa.JSON(), nullable=False, server_default='[]'))
    _add_column_if_missing('milestones', sa.Column('planned_start', sa.Date(), nullable=True))
    _add_column_if_missing('milestones', sa.Column('planned_end', sa.Date(), nullable=True))
    _add_column_if_missing('milestones', sa.Column('lifecycle_state', sa.String(), nullable=False, server_default='Agreement Drafted'))

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'committee_decisions' not in tables:
        op.create_table(
            'committee_decisions',
            sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('challenge_id', sa.String(), nullable=False),
            sa.Column('startup_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('recorded_by', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('decision', sa.String(), nullable=False),
            sa.Column('dissent', sa.String(), nullable=False, server_default=''),
            sa.Column('responsibilities', sa.JSON(), nullable=False, server_default='[]'),
            sa.Column('reason', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['challenge_id'], ['challenges.id']),
            sa.ForeignKeyConstraint(['startup_id'], ['startups.id']),
            sa.ForeignKeyConstraint(['recorded_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'agreement_templates' not in tables:
        op.create_table(
            'agreement_templates',
            sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('template_key', sa.String(), nullable=False),
            sa.Column('version', sa.Integer(), nullable=False),
            sa.Column('label', sa.String(), nullable=False),
            sa.Column('clauses', sa.JSON(), nullable=False),
            sa.Column('published', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['created_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
    indexes = {item['name'] for item in sa.inspect(op.get_bind()).get_indexes('agreement_templates')}
    if 'ix_agreement_templates_template_key' not in indexes:
        op.create_index('ix_agreement_templates_template_key', 'agreement_templates', ['template_key'])

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if 'startup_officer_questions' not in tables:
        op.create_table(
            'startup_officer_questions',
            sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
            sa.Column('agreement_id', sa.String(), nullable=False),
            sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('author_role', sa.String(), nullable=False),
            sa.Column('body', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['agreement_id'], ['pilot_agreements.id']),
            sa.ForeignKeyConstraint(['author_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if 'startup_officer_questions' in tables:
        op.drop_table('startup_officer_questions')
    if 'agreement_templates' in tables:
        indexes = {item['name'] for item in sa.inspect(bind).get_indexes('agreement_templates')}
        if 'ix_agreement_templates_template_key' in indexes:
            op.drop_index('ix_agreement_templates_template_key', table_name='agreement_templates')
        op.drop_table('agreement_templates')
    if 'committee_decisions' in tables:
        op.drop_table('committee_decisions')
    for table, columns in {
        'milestones': ('lifecycle_state', 'planned_end', 'planned_start', 'linked_kpis', 'acceptance_criteria', 'evidence_requirements'),
        'agreement_versions': ('approved', 'change_note', 'clauses', 'template_version', 'template_key'),
        'pilot_agreements': ('created_by', 'approval_chain', 'terms_accepted'),
        'evaluations': ('submitted',),
        'rubric_versions': ('criteria',),
    }.items():
        current_tables = set(sa.inspect(bind).get_table_names())
        if table not in current_tables:
            continue
        current_columns = {item['name'] for item in sa.inspect(bind).get_columns(table)}
        for column in columns:
            if column in current_columns:
                op.drop_column(table, column)
