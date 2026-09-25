"""dynamic persona engine + phase 3/4: persona profiles, lorebook, diary,
mirror questions, quests, capsules, recap cards, media, hearts, user mood

Revision ID: c5d9e4f12a78
Revises: b3f7a2c91d04
Create Date: 2026-09-02

§13 dynamic persona + Phase 3 (voice & media) + Phase 4 (growth loops):
- saathi_sessions: user_mood + user_mood_updated_at (realtime detection)
- new: saathi_persona_profiles, saathi_lorebook_entries, saathi_diary_entries,
  saathi_mirror_questions, saathi_quests, saathi_moment_capsules,
  saathi_recap_cards, saathi_media_items, saathi_heart_ledger
"""
import sqlalchemy as sa
from alembic import op

revision = 'c5d9e4f12a78'
down_revision = 'b3f7a2c91d04'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('saathi_sessions', sa.Column('user_mood', sa.String(24), nullable=True))
    op.add_column('saathi_sessions', sa.Column('user_mood_updated_at', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'saathi_persona_profiles',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(),
                  sa.ForeignKey('saathi_sessions.id'), nullable=False, unique=True, index=True),
        sa.Column('traits', sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column('persona_prompt', sa.Text(), nullable=True),
        sa.Column('style_mining_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('style_digest', sa.JSON(), nullable=True),
        sa.Column('evolution_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('evolved_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'saathi_lorebook_entries',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('key', sa.String(120), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('source', sa.String(16), server_default='user', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )

    op.create_table(
        'saathi_diary_entries',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('day_key', sa.String(10), nullable=False),
        sa.Column('title', sa.String(160), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('mood', sa.String(24), nullable=True),
        sa.Column('illustrated_url', sa.String(512), nullable=True),
        sa.Column('reaction', sa.String(8), nullable=True),
    )

    op.create_table(
        'saathi_mirror_questions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('reflection', sa.Text(), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'saathi_quests',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('title', sa.String(160), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('kind', sa.String(24), server_default='duo', nullable=False),
        sa.Column('target', sa.Integer(), server_default='1', nullable=False),
        sa.Column('progress', sa.Integer(), server_default='0', nullable=False),
        sa.Column('reward_points', sa.Integer(), server_default='10', nullable=False),
        sa.Column('status', sa.String(16), server_default='active', nullable=False),
        sa.Column('freeze_used', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'saathi_moment_capsules',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('title', sa.String(160), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('author', sa.String(16), server_default='companion', nullable=False),
        sa.Column('unlock_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'saathi_recap_cards',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('period', sa.String(24), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('share_token', sa.String(32), nullable=False, unique=True),
        sa.Column('watermark', sa.String(64), server_default='AI companion · Milan', nullable=False),
    )

    op.create_table(
        'saathi_media_items',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), sa.ForeignKey('saathi_sessions.id'), nullable=False, index=True),
        sa.Column('kind', sa.String(24), server_default='selfie', nullable=False),
        sa.Column('url', sa.String(512), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('ai_label', sa.String(64), server_default='AI-illustrated', nullable=False),
        sa.Column('pack_id', sa.String(36), nullable=True),
    )

    op.create_table(
        'saathi_heart_ledger',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('delta', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(64), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    for table in ('saathi_heart_ledger', 'saathi_media_items', 'saathi_recap_cards',
                  'saathi_moment_capsules', 'saathi_quests', 'saathi_mirror_questions',
                  'saathi_diary_entries', 'saathi_lorebook_entries',
                  'saathi_persona_profiles'):
        op.drop_table(table)
    op.drop_column('saathi_sessions', 'user_mood_updated_at')
    op.drop_column('saathi_sessions', 'user_mood')
