"""fix users table columns: rename nome->name, password->password_hash, add document

Revision ID: fix_users_columns
Revises: 5a6be0697e34
Create Date: 2026-08-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'fix_users_columns'
down_revision: Union[str, Sequence[str], None] = '5a6be0697e34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c['name'] for c in inspector.get_columns('users')}

    if 'nome' in cols and 'name' not in cols:
        op.alter_column('users', 'nome', new_column_name='name',
                        existing_type=sa.String(length=255), existing_nullable=False)

    if 'password' in cols and 'password_hash' not in cols:
        op.alter_column('users', 'password', new_column_name='password_hash',
                        existing_type=sa.String(length=255), existing_nullable=False)

    if 'document' not in cols:
        op.add_column('users', sa.Column('document', sa.String(length=32), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = {c['name'] for c in inspector.get_columns('users')}

    if 'document' in cols:
        op.drop_column('users', 'document')

    if 'password_hash' in cols and 'password' not in cols:
        op.alter_column('users', 'password_hash', new_column_name='password',
                        existing_type=sa.String(length=255), existing_nullable=False)

    if 'name' in cols and 'nome' not in cols:
        op.alter_column('users', 'name', new_column_name='nome',
                        existing_type=sa.String(length=255), existing_nullable=False)
