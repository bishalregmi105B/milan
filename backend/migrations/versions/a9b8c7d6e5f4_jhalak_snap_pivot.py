"""Jhalak v2 pivot: view-once image snaps

New tables:
- jhalak_snaps       24h ephemeral image snaps (one-time view per person)
- jhalak_snap_views  per-viewer burn tracking (unique snap+viewer) with
                     self-reported screenshot detection

The legacy `reels` tables stay untouched — video reels are deprecated in the
app but the rows remain for account history.

Revision ID: a9b8c7d6e5f4
Revises: f1a2b3c4d5e6
Create Date: 2026-09-02
"""
import sqlalchemy as sa
from alembic import op

revision = 'a9b8c7d6e5f4'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _existing_tables()
    if 'jhalak_snaps' not in tables:
        op.create_table(
            'jhalak_snaps',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('user_id', sa.Uuid(), nullable=False),
            sa.Column('image_url', sa.String(length=512), nullable=False),
            sa.Column('caption', sa.String(length=280), nullable=True),
            sa.Column('filter_key', sa.String(length=24), nullable=True),
            sa.Column('posted_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('view_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_jhalak_snaps_user_id', 'jhalak_snaps', ['user_id'])
        op.create_index('ix_jhalak_snaps_expires_at', 'jhalak_snaps', ['expires_at'])

    if 'jhalak_snap_views' not in tables:
        op.create_table(
            'jhalak_snap_views',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('snap_id', sa.Uuid(), nullable=False),
            sa.Column('viewer_id', sa.Uuid(), nullable=False),
            sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('screenshot_detected', sa.Boolean(),
                      server_default=sa.text('false'), nullable=False),
            sa.ForeignKeyConstraint(['snap_id'], ['jhalak_snaps.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['viewer_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('snap_id', 'viewer_id', name='uq_jhalak_view_once'),
        )
        op.create_index('ix_jhalak_snap_views_snap_id', 'jhalak_snap_views', ['snap_id'])
        op.create_index('ix_jhalak_snap_views_viewer_id', 'jhalak_snap_views', ['viewer_id'])


def downgrade() -> None:
    op.drop_table('jhalak_snap_views')
    op.drop_table('jhalak_snaps')
