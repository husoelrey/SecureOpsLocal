"""Add feedback table

Revision ID: 5c2d3e4f5a6b
Revises: 3abd85671fc1
Create Date: 2026-08-24 11:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5c2d3e4f5a6b'
down_revision: Union[str, None] = '3abd85671fc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_id', sa.String(), nullable=False),
        sa.Column('is_false_positive', sa.Boolean(), nullable=False),
        sa.Column('admin_notes', sa.Text(), nullable=False),
        sa.Column('source_ip', sa.String(), nullable=True),
        sa.Column('target_user', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)
    op.create_index(op.f('ix_feedback_incident_id'), 'feedback', ['incident_id'], unique=False)
    op.create_index(op.f('ix_feedback_source_ip'), 'feedback', ['source_ip'], unique=False)
    op.create_index(op.f('ix_feedback_target_user'), 'feedback', ['target_user'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_target_user'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_source_ip'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_incident_id'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_table('feedback')
