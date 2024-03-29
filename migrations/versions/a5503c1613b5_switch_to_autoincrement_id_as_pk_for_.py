"""Switch to autoincrement id as pk for farming_info_events

Revision ID: a5503c1613b5
Revises: 2d3d4960ffe8
Create Date: 2021-07-15 00:59:30.540391

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a5503c1613b5'
down_revision = '2d3d4960ffe8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table('farming_info_events', schema=None) as batch_op:
            batch_op.drop_constraint('pk_farming_info_events')
            batch_op.add_column(sa.Column('id', sa.Integer(), autoincrement=True, nullable=False))
            batch_op.create_index(batch_op.f('ix_farming_info_events_ts'), ['ts'], unique=False)
            batch_op.create_primary_key('pk_farming_info_events', ['id'])
    except ValueError:
        with op.batch_alter_table('farming_info_events', schema=None) as batch_op:
            batch_op.add_column(sa.Column('id', sa.Integer(), autoincrement=True, nullable=False))
            batch_op.create_index(batch_op.f('ix_farming_info_events_ts'), ['ts'], unique=False)
            batch_op.create_primary_key('pk_farming_info_events', ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        with op.batch_alter_table('farming_info_events', schema=None) as batch_op:
            batch_op.drop_constraint('pk_farming_info_events')
            batch_op.drop_index(batch_op.f('ix_farming_info_events_ts'))
            batch_op.create_primary_key('pk_farming_info_events', ['ts'])
            batch_op.drop_column('id')
    except ValueError:
        with op.batch_alter_table('farming_info_events', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_farming_info_events_ts'))
            batch_op.create_primary_key('pk_farming_info_events', ['ts'])
            batch_op.drop_column('id')
    # ### end Alembic commands ###
