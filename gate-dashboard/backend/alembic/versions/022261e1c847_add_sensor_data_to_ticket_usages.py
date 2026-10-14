"""Add sensor_data_json to ticket_usages

Revision ID: 022261e1c847
Revises: 001
Create Date: 2026-10-12 06:15:51.623000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '022261e1c847'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add sensor_data_json column to ticket_usages
    op.add_column('ticket_usages', sa.Column('sensor_data_json', sa.Text(), nullable=True))


def downgrade():
    # Remove sensor_data_json column
    op.drop_column('ticket_usages', 'sensor_data_json')
