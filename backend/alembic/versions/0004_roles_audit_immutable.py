"""Normalize role definitions and enforce append-only audit rows.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

ROLES = [
    ('officer', 'Officer', 'Publishes challenges and records procurement decisions.'),
    ('startup', 'Startup Applicant', 'Submits applications, evidence, and invoices.'),
    ('evaluator', 'Evaluator', 'Scores applications when no conflict is declared.'),
    ('validator', 'Validator', 'Independently reviews submitted evidence.'),
    ('finance', 'Finance', 'Reviews invoices and records payment status.'),
    ('district', 'Receiving District', 'Reviews transfer readiness for district adoption.'),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if 'roles' not in inspector.get_table_names():
        op.create_table(
            'roles',
            sa.Column('name', sa.String(length=40), primary_key=True),
            sa.Column('label', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=250), nullable=False),
        )
    bind = op.get_bind()
    role_table = sa.table('roles', sa.column('name', sa.String()), sa.column('label', sa.String()), sa.column('description', sa.String()))
    for name, label, description in ROLES:
        if not bind.execute(sa.select(role_table.c.name).where(role_table.c.name == name)).first():
            bind.execute(role_table.insert().values(name=name, label=label, description=description))

    if bind.dialect.name == 'postgresql':
        role_foreign_key_exists = any('role' in item.get('constrained_columns', []) for item in sa.inspect(bind).get_foreign_keys('users'))
        if not role_foreign_key_exists:
            op.create_foreign_key('fk_users_role', 'users', 'roles', ['role'], ['name'])
        op.execute("""
        CREATE OR REPLACE FUNCTION pilotproof_audit_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit_event rows are append-only'; END; $$;
        """)
        op.execute("DROP TRIGGER IF EXISTS audit_no_update ON audit_event")
        op.execute("DROP TRIGGER IF EXISTS audit_no_delete ON audit_event")
        op.execute("CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_event FOR EACH ROW EXECUTE FUNCTION pilotproof_audit_immutable()")
        op.execute("CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_event FOR EACH ROW EXECUTE FUNCTION pilotproof_audit_immutable()")
        op.execute("DROP TRIGGER IF EXISTS lifecycle_audit_no_update ON audit_events")
        op.execute("DROP TRIGGER IF EXISTS lifecycle_audit_no_delete ON audit_events")
        op.execute("CREATE TRIGGER lifecycle_audit_no_update BEFORE UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION pilotproof_audit_immutable()")
        op.execute("CREATE TRIGGER lifecycle_audit_no_delete BEFORE DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION pilotproof_audit_immutable()")
    elif bind.dialect.name == 'sqlite':
        op.execute("CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END")
        op.execute("CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_event BEGIN SELECT RAISE(ABORT, 'audit_event rows are append-only'); END")
        op.execute("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END")
        op.execute("CREATE TRIGGER IF NOT EXISTS lifecycle_audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit_events rows are append-only'); END")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute('DROP TRIGGER IF EXISTS audit_no_delete ON audit_event')
        op.execute('DROP TRIGGER IF EXISTS audit_no_update ON audit_event')
        op.execute('DROP TRIGGER IF EXISTS lifecycle_audit_no_delete ON audit_events')
        op.execute('DROP TRIGGER IF EXISTS lifecycle_audit_no_update ON audit_events')
        op.execute('DROP FUNCTION IF EXISTS pilotproof_audit_immutable()')
        op.drop_constraint('fk_users_role', 'users', type_='foreignkey')
    elif bind.dialect.name == 'sqlite':
        op.execute('DROP TRIGGER IF EXISTS audit_no_delete')
        op.execute('DROP TRIGGER IF EXISTS audit_no_update')
        op.execute('DROP TRIGGER IF EXISTS lifecycle_audit_no_delete')
        op.execute('DROP TRIGGER IF EXISTS lifecycle_audit_no_update')
    op.drop_table('roles')
