"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-09-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # passages table (existing from ESP32)
    op.create_table(
        'passages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('method', sa.String(length=16), nullable=False),
        sa.Column('uid', sa.String(length=64), nullable=True),
        sa.Column('plate', sa.String(length=32), nullable=True),
        sa.Column('allowed', sa.Boolean(), nullable=False),
        sa.Column('image_path', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_passages_direction_ts', 'passages', ['direction', 'ts'], unique=False)
    op.create_index('ix_passages_method', 'passages', ['method'], unique=False)

    # users table
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=128), nullable=True),
        sa.Column('hashed_password', sa.String(length=128), nullable=False),
        sa.Column('full_name', sa.String(length=128), nullable=True),
        sa.Column('role', sa.Enum('ADMIN', 'GUARD', 'STAFF', name='userrole'), nullable=False, default='STAFF'),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_active_role', 'users', ['active', 'role'], unique=False)

    # authorized_cards table
    op.create_table(
        'authorized_cards',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('uid', sa.String(length=32), nullable=False),
        sa.Column('label', sa.String(length=64), nullable=True),
        sa.Column('added_by', sa.String(length=64), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('active', sa.Boolean(), nullable=False, default=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_authorized_cards_uid', 'authorized_cards', ['uid'], unique=True)
    op.create_index('ix_authorized_cards_active', 'authorized_cards', ['active'], unique=False)

    # ticket_tokens table
    op.create_table(
        'ticket_tokens',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('qr_payload', sa.Text(), nullable=False),
        sa.Column('type', sa.Enum('SINGLE_ENTRY', 'MULTI_DAY', 'VIP', 'STAFF', name='tickettype'), nullable=False, default='SINGLE_ENTRY'),
        sa.Column('valid_from', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=False, default=1),
        sa.Column('used_count', sa.Integer(), nullable=False, default=0),
        sa.Column('issued_by', sa.String(length=64), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('revoked', sa.Boolean(), nullable=False, default=False),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticket_tokens_code', 'ticket_tokens', ['code'], unique=True)
    op.create_index('ix_ticket_tokens_valid_until', 'ticket_tokens', ['valid_until'], unique=False)
    op.create_index('ix_ticket_tokens_revoked', 'ticket_tokens', ['revoked'], unique=False)

    # ticket_usages table
    op.create_table(
        'ticket_usages',
        sa.Column('id', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column('token_id', UUID(as_uuid=True), nullable=False),
        sa.Column('gate_id', sa.String(length=16), nullable=False),
        sa.Column('direction', sa.String(length=8), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, default=sa.func.now()),
        sa.Column('allowed', sa.Boolean(), nullable=False),
        sa.Column('method', sa.Enum('QR_SCAN', 'RFID_LINK', 'MANUAL', 'ANPR', name='validationmethod'), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['token_id'], ['ticket_tokens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ticket_usages_token_id', 'ticket_usages', ['token_id'], unique=False)
    op.create_index('ix_ticket_usages_gate_timestamp', 'ticket_usages', ['gate_id', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ticket_usages_gate_timestamp', table_name='ticket_usages')
    op.drop_index('ix_ticket_usages_token_id', table_name='ticket_usages')
    op.drop_table('ticket_usages')

    op.drop_index('ix_ticket_tokens_revoked', table_name='ticket_tokens')
    op.drop_index('ix_ticket_tokens_valid_until', table_name='ticket_tokens')
    op.drop_index('ix_ticket_tokens_code', table_name='ticket_tokens')
    op.drop_table('ticket_tokens')

    op.drop_index('ix_authorized_cards_active', table_name='authorized_cards')
    op.drop_index('ix_authorized_cards_uid', table_name='authorized_cards')
    op.drop_table('authorized_cards')

    op.drop_index('ix_users_active_role', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')

    op.drop_index('ix_passages_method', table_name='passages')
    op.drop_index('ix_passages_direction_ts', table_name='passages')
    op.drop_table('passages')