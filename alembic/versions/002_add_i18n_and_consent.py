"""Add i18n and user consent fields

Revision ID: 002
Revises: 001
Create Date: 2025-12-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add language field for i18n
    op.add_column('users', sa.Column(
        'language',
        sa.String(5),
        nullable=False,
        server_default='en'
    ))
    op.create_index('idx_users_language', 'users', ['language'])

    # Add user consent fields for Privacy Policy and Terms of Service
    op.add_column('users', sa.Column(
        'consent_privacy_policy',
        sa.Boolean(),
        nullable=False,
        server_default='false'
    ))
    op.add_column('users', sa.Column(
        'consent_terms_of_service',
        sa.Boolean(),
        nullable=False,
        server_default='false'
    ))
    op.add_column('users', sa.Column(
        'consent_date',
        sa.DateTime(),
        nullable=True
    ))
    op.add_column('users', sa.Column(
        'consent_ip',
        sa.String(45),  # IPv6 support
        nullable=True
    ))

    # Index for finding users without consent
    op.create_index(
        'idx_users_consent',
        'users',
        ['consent_privacy_policy', 'consent_terms_of_service']
    )


def downgrade() -> None:
    op.drop_index('idx_users_consent', 'users')
    op.drop_column('users', 'consent_ip')
    op.drop_column('users', 'consent_date')
    op.drop_column('users', 'consent_terms_of_service')
    op.drop_column('users', 'consent_privacy_policy')
    op.drop_index('idx_users_language', 'users')
    op.drop_column('users', 'language')
