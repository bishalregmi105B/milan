"""email auth: nullable phone, email column, auth_provider

Revision ID: a7c1e94b02dd
Revises: 4feb8259c2b4
Create Date: 2026-08-30

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c1e94b02dd'
down_revision = '4feb8259c2b4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(length=16),
                                     nullable=False, server_default='phone'))
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
    # Email-first accounts have no phone, so phone becomes optional.
    op.alter_column('users', 'phone', existing_type=sa.String(length=20), nullable=True)


def downgrade():
    op.alter_column('users', 'phone', existing_type=sa.String(length=20), nullable=False)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'email')
