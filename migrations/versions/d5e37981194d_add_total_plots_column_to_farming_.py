"""Add total_plots column to farming events table

Revision ID: d5e37981194d
Revises: 0d96de75543b
Create Date: 2021-06-13 00:59:28.824233

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd5e37981194d'
down_revision = '0d96de75543b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('farming_info_events', sa.Column('total_plots', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('farming_info_events', 'total_plots')
    # ### end Alembic commands ###
