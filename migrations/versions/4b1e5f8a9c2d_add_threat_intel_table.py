"""Add threat_intel table

Revision ID: 4b1e5f8a9c2d
Revises: 3abd85671fc1
Create Date: 2026-08-24 10:55:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4b1e5f8a9c2d'
down_revision: Union[str, None] = '3abd85671fc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'threat_intel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=False),
        sa.Column('threat_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_threat_intel_id'), 'threat_intel', ['id'], unique=False)
    op.create_index(op.f('ix_threat_intel_ip_address'), 'threat_intel', ['ip_address'], unique=True)
    op.create_index(op.f('ix_threat_intel_threat_type'), 'threat_intel', ['threat_type'], unique=False)
    op.create_index(op.f('ix_threat_intel_severity'), 'threat_intel', ['severity'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_threat_intel_severity'), table_name='threat_intel')
    op.drop_index(op.f('ix_threat_intel_threat_type'), table_name='threat_intel')
    op.drop_index(op.f('ix_threat_intel_ip_address'), table_name='threat_intel')
    op.drop_index(op.f('ix_threat_intel_id'), table_name='threat_intel')
    op.drop_table('threat_intel')
