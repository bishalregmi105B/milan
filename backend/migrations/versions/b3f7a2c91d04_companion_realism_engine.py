"""companion realism engine: romantic roster, presence, status posts, open loops

Revision ID: b3f7a2c91d04
Revises: a7c1e94b02dd
Create Date: 2026-09-02

Master plan §7.1 — companion-mode schema:
- saathi_characters: companion roster extensions (tier locks, texting style,
  voice, backstory)
- saathi_sessions: companion_mode + intimacy progression + streak/status caps
- saathi_messages: message_type (proactive messages land in the chat) + meta
- saathi_memory_items: pin/importance (memory shaping)
- new: saathi_presence_schedules, saathi_status_posts, saathi_open_loops
"""
import sqlalchemy as sa
from alembic import op

revision = 'b3f7a2c91d04'
down_revision = 'a7c1e94b02dd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('saathi_characters', sa.Column('companion_enabled', sa.Boolean(),
                                                 server_default=sa.text('false'), nullable=False))
    op.add_column('saathi_characters', sa.Column('min_tier', sa.String(16),
                                                 server_default='free', nullable=False))
    op.add_column('saathi_characters', sa.Column('relationship_style', sa.String(32), nullable=True))
    op.add_column('saathi_characters', sa.Column('texting_style', sa.JSON(), nullable=True))
    op.add_column('saathi_characters', sa.Column('voice_id', sa.String(128), nullable=True))
    op.add_column('saathi_characters', sa.Column('avatar_urls', sa.JSON(), nullable=True))
    op.add_column('saathi_characters', sa.Column('backstory_template', sa.Text(), nullable=True))

    op.add_column('saathi_sessions', sa.Column('companion_mode', sa.String(16),
                                               server_default='practice', nullable=False))
    op.add_column('saathi_sessions', sa.Column('intimacy_level', sa.Integer(),
                                               server_default='0', nullable=False))
    op.add_column('saathi_sessions', sa.Column('bond_points', sa.Integer(),
                                               server_default='0', nullable=False))
    op.add_column('saathi_sessions', sa.Column('current_mood', sa.String(24),
                                               server_default='cheerful', nullable=False))
    op.add_column('saathi_sessions', sa.Column('streak_days', sa.Integer(),
                                               server_default='0', nullable=False))
    op.add_column('saathi_sessions', sa.Column('last_streak_date', sa.String(10), nullable=True))
    op.add_column('saathi_sessions', sa.Column('status_posts_today', sa.Integer(),
                                               server_default='0', nullable=False))
    op.add_column('saathi_sessions', sa.Column('status_cap_date', sa.String(10), nullable=True))

    op.add_column('saathi_messages', sa.Column('message_type', sa.String(24),
                                               server_default='chat', nullable=False))
    op.add_column('saathi_messages', sa.Column('meta', sa.JSON(), nullable=True))

    op.add_column('saathi_memory_items', sa.Column('is_pinned', sa.Boolean(),
                                                   server_default=sa.text('false'), nullable=False))
    op.add_column('saathi_memory_items', sa.Column('importance', sa.Float(),
                                                   server_default='0.5', nullable=False))

    op.create_table(
        'saathi_presence_schedules',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('character_id', sa.Uuid(),
                  sa.ForeignKey('saathi_characters.id'), nullable=False, unique=True),
        sa.Column('schedule', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'saathi_status_posts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('session_id', sa.Uuid(),
                  sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False, server_default='ambient'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reaction', sa.String(8), nullable=True),
        sa.Column('reacted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'saathi_open_loops',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('session_id', sa.Uuid(),
                  sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('followup_after_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('status', sa.String(16), nullable=False, server_default='open'),
        sa.Column('last_callback_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('saathi_open_loops')
    op.drop_table('saathi_status_posts')
    op.drop_table('saathi_presence_schedules')
    op.drop_column('saathi_memory_items', 'importance')
    op.drop_column('saathi_memory_items', 'is_pinned')
    op.drop_column('saathi_messages', 'meta')
    op.drop_column('saathi_messages', 'message_type')
    op.drop_column('saathi_sessions', 'status_cap_date')
    op.drop_column('saathi_sessions', 'status_posts_today')
    op.drop_column('saathi_sessions', 'last_streak_date')
    op.drop_column('saathi_sessions', 'streak_days')
    op.drop_column('saathi_sessions', 'current_mood')
    op.drop_column('saathi_sessions', 'bond_points')
    op.drop_column('saathi_sessions', 'intimacy_level')
    op.drop_column('saathi_sessions', 'companion_mode')
    op.drop_column('saathi_characters', 'backstory_template')
    op.drop_column('saathi_characters', 'avatar_urls')
    op.drop_column('saathi_characters', 'voice_id')
    op.drop_column('saathi_characters', 'texting_style')
    op.drop_column('saathi_characters', 'relationship_style')
    op.drop_column('saathi_characters', 'min_tier')
    op.drop_column('saathi_characters', 'companion_enabled')
