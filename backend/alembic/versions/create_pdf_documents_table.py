"""create pdf_documents table

Revision ID: create_pdf_documents
Revises: create_automation_history
Create Date: 2026-08-12 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'create_pdf_documents'
down_revision: Union[str, Sequence[str], None] = 'create_automation_history'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pdf_documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('automation_history_id', sa.Integer(), nullable=True),
        sa.Column('consultant_name', sa.String(length=255), nullable=False),
        sa.Column('quota', sa.String(length=64), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False, server_default='application/pdf'),
        sa.Column('size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['automation_history_id'], ['automation_history.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pdf_documents_id'), 'pdf_documents', ['id'], unique=False)
    op.create_index(op.f('ix_pdf_documents_automation_history_id'), 'pdf_documents', ['automation_history_id'], unique=False)
    op.create_index(op.f('ix_pdf_documents_created_at'), 'pdf_documents', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_pdf_documents_created_at'), table_name='pdf_documents')
    op.drop_index(op.f('ix_pdf_documents_automation_history_id'), table_name='pdf_documents')
    op.drop_index(op.f('ix_pdf_documents_id'), table_name='pdf_documents')
    op.drop_table('pdf_documents')
