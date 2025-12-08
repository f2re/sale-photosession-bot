"""Initial migration for Product Photoshoot Bot

Revision ID: 001
Revises: 
Create Date: 2025-10-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.Column('first_name', sa.String(length=255), nullable=True),
    sa.Column('last_name', sa.String(length=255), nullable=True),
    sa.Column('images_remaining', sa.Integer(), nullable=False),
    sa.Column('total_images_processed', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('utm_source', sa.String(length=255), nullable=True),
    sa.Column('utm_medium', sa.String(length=255), nullable=True),
    sa.Column('utm_campaign', sa.String(length=255), nullable=True),
    sa.Column('utm_content', sa.String(length=255), nullable=True),
    sa.Column('utm_term', sa.String(length=255), nullable=True),
    sa.Column('metrika_client_id', sa.String(length=36), nullable=True),
    sa.Column('referred_by_id', sa.Integer(), nullable=True),
    sa.Column('referral_code', sa.String(length=20), nullable=True),
    sa.Column('total_referrals', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['referred_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('telegram_id')
    )
    op.create_index(op.f('ix_users_metrika_client_id'), 'users', ['metrika_client_id'], unique=True)
    op.create_index(op.f('ix_users_referral_code'), 'users', ['referral_code'], unique=True)
    op.create_index(op.f('ix_users_referred_by_id'), 'users', ['referred_by_id'], unique=False)
    op.create_index(op.f('ix_users_utm_campaign'), 'users', ['utm_campaign'], unique=False)
    op.create_index(op.f('ix_users_utm_medium'), 'users', ['utm_medium'], unique=False)
    op.create_index(op.f('ix_users_utm_source'), 'users', ['utm_source'], unique=False)

    # Create packages table
    op.create_table('packages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('photoshoots_count', sa.Integer(), nullable=False),
    sa.Column('price_rub', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    # Create orders table
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('package_id', sa.Integer(), nullable=False),
    sa.Column('invoice_id', sa.String(length=255), nullable=True),
    sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('paid_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('invoice_id')
    )

    # Create processed_images table
    op.create_table('processed_images',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('telegram_file_id', sa.String(length=255), nullable=True),
    sa.Column('original_file_id', sa.String(length=255), nullable=True),
    sa.Column('processed_file_id', sa.String(length=255), nullable=True),
    sa.Column('style_name', sa.String(length=255), nullable=True),
    sa.Column('prompt_used', sa.Text(), nullable=True),
    sa.Column('aspect_ratio', sa.String(length=50), nullable=True),
    sa.Column('is_free', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create style_presets table
    op.create_table('style_presets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('style_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_style_presets_id'), 'style_presets', ['id'], unique=False)

    # Create support_tickets table
    op.create_table('support_tickets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('admin_response', sa.Text(), nullable=True),
    sa.Column('admin_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create support_messages table
    op.create_table('support_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('sender_telegram_id', sa.BigInteger(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create admins table
    op.create_table('admins',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
    sa.Column('username', sa.String(length=255), nullable=True),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('telegram_id')
    )

    # Create utm_events table
    op.create_table('utm_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('metrika_client_id', sa.String(length=36), nullable=True),
    sa.Column('event_value', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('sent_to_metrika', sa.Boolean(), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.Column('metrika_upload_id', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_utm_events_created', 'utm_events', ['created_at'], unique=False)
    op.create_index('idx_utm_events_sent', 'utm_events', ['sent_to_metrika'], unique=False)
    op.create_index('idx_utm_events_user_type', 'utm_events', ['user_id', 'event_type'], unique=False)
    op.create_index(op.f('ix_utm_events_event_type'), 'utm_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_utm_events_metrika_client_id'), 'utm_events', ['metrika_client_id'], unique=False)

    # Create referral_rewards table
    op.create_table('referral_rewards',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('referred_user_id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('reward_type', sa.String(length=50), nullable=False),
    sa.Column('images_rewarded', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['referred_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_referral_rewards_created', 'referral_rewards', ['created_at'], unique=False)
    op.create_index('idx_referral_rewards_user_type', 'referral_rewards', ['user_id', 'reward_type'], unique=False)
    op.create_index(op.f('ix_referral_rewards_reward_type'), 'referral_rewards', ['reward_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_referral_rewards_reward_type'), table_name='referral_rewards')
    op.drop_index('idx_referral_rewards_user_type', table_name='referral_rewards')
    op.drop_index('idx_referral_rewards_created', table_name='referral_rewards')
    op.drop_table('referral_rewards')
    op.drop_index(op.f('ix_utm_events_metrika_client_id'), table_name='utm_events')
    op.drop_index(op.f('ix_utm_events_event_type'), table_name='utm_events')
    op.drop_index('idx_utm_events_user_type', table_name='utm_events')
    op.drop_index('idx_utm_events_sent', table_name='utm_events')
    op.drop_index('idx_utm_events_created', table_name='utm_events')
    op.drop_table('utm_events')
    op.drop_table('admins')
    op.drop_table('support_messages')
    op.drop_table('support_tickets')
    op.drop_index(op.f('ix_style_presets_id'), table_name='style_presets')
    op.drop_table('style_presets')
    op.drop_table('processed_images')
    op.drop_table('orders')
    op.drop_table('packages')
    op.drop_index(op.f('ix_users_utm_source'), table_name='users')
    op.drop_index(op.f('ix_users_utm_medium'), table_name='users')
    op.drop_index(op.f('ix_users_utm_campaign'), table_name='users')
    op.drop_index(op.f('ix_users_referred_by_id'), table_name='users')
    op.drop_index(op.f('ix_users_referral_code'), table_name='users')
    op.drop_index(op.f('ix_users_metrika_client_id'), table_name='users')
    op.drop_table('users')
