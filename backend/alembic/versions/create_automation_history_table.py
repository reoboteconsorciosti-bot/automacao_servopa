"""create automation_history table

Revision ID: create_automation_history
Revises: fix_users_columns
Create Date: 2026-08-12 11:26:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'create_automation_history'
down_revision: Union[str, Sequence[str], None] = 'fix_users_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'automation_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_name', sa.String(length=255), nullable=False),
        sa.Column('user_email', sa.String(length=255), nullable=False),
        sa.Column('consultant_name', sa.String(length=255), nullable=False),
        sa.Column('quotas_summary', sa.Text(), nullable=True),
        sa.Column('quotas_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='running'),
        sa.Column('pdf_filename', sa.String(length=255), nullable=True),
        sa.Column('pdf_path', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_automation_history_id'), 'automation_history', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_automation_history_id'), table_name='automation_history')
    op.drop_table('automation_history')
