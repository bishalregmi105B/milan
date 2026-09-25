"""doc 8: companion realism engine v2 + full-system upgrades

Adds:
- saathi_characters: persona_bible, age, birthday, hometown
- saathi_sessions: user_style, rolling_summary, summary_upto_message_at,
  awaiting_user_reply, deferred_reply_at, deferred_reply_body
- saathi_memory_items: last_recalled_at
- messages: media_type, media_duration_ms
- profiles: interview_answers
- users: trust_score, deleted_at, last_active_at
- matches: expires_at, last_activity_at, expiry_warned_at
- NEW interests, profile_views
- DATA: companion_mode 'practice' -> 'dating', companion_enabled = true

Idempotent: a partially-applied run of this revision (interrupted deploy)
left some columns behind with the version pointer un-bumped. Every step
re-checks the schema so the migration completes whatever is missing.

Revision ID: f1a2b3c4d5e6
Revises: e9f2a3b4c5d6
Create Date: 2026-09-02
"""
import sqlalchemy as sa
from alembic import op

revision = 'f1a2b3c4d5e6'
down_revision = 'e9f2a3b4c5d6'
branch_labels = None
depends_on = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _existing_indexes(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {i["name"] for i in inspector.get_indexes(table)}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _existing_columns(table):
        op.add_column(table, column)


def _create_index_if_missing(name: str, table: str, columns: list[str]) -> None:
    if name not in _existing_indexes(table):
        op.create_index(name, table, columns)


def upgrade() -> None:
    # ── companion persona + day ────────────────────────────────────────────
    _add_column_if_missing('saathi_characters', sa.Column('persona_bible', sa.JSON(), nullable=True))
    _add_column_if_missing('saathi_characters', sa.Column('age', sa.Integer(), nullable=True))
    _add_column_if_missing('saathi_characters', sa.Column('birthday', sa.String(length=5), nullable=True))
    _add_column_if_missing('saathi_characters', sa.Column('hometown', sa.String(length=120), nullable=True))

    # ── language mirroring + context compaction + deferred replies ────────
    _add_column_if_missing('saathi_sessions', sa.Column('user_style', sa.JSON(), nullable=True))
    _add_column_if_missing('saathi_sessions', sa.Column('rolling_summary', sa.Text(), nullable=True))
    _add_column_if_missing('saathi_sessions', sa.Column(
        'summary_upto_message_at', sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing('saathi_sessions', sa.Column(
        'awaiting_user_reply', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    _add_column_if_missing('saathi_sessions', sa.Column(
        'deferred_reply_at', sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing('saathi_sessions', sa.Column('deferred_reply_body', sa.Text(), nullable=True))
    _add_column_if_missing('saathi_memory_items', sa.Column(
        'last_recalled_at', sa.DateTime(timezone=True), nullable=True))

    # ── chat media typing (image | gif | audio) ───────────────────────────
    _add_column_if_missing('messages', sa.Column('media_type', sa.String(length=16), nullable=True))
    _add_column_if_missing('messages', sa.Column('media_duration_ms', sa.Integer(), nullable=True))
    # Backfill: every existing media row was an image upload (video was never
    # allowed in chat), so nothing renders as an untyped blob after deploy.
    op.execute("UPDATE messages SET media_type = 'image' "
               "WHERE media_url IS NOT NULL AND media_type IS NULL")

    # ── profile: verbatim interview answers ───────────────────────────────
    _add_column_if_missing('profiles', sa.Column(
        'interview_answers', sa.JSON(), server_default=sa.text("'[]'"), nullable=False))

    # ── users: trust, soft delete, activity ───────────────────────────────
    _add_column_if_missing('users', sa.Column(
        'trust_score', sa.Integer(), server_default=sa.text('50'), nullable=False))
    _add_column_if_missing('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing('users', sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True))
    _create_index_if_missing('ix_users_deleted_at', 'users', ['deleted_at'])
    # Existing accounts have been active at least once — seed from created_at so
    # activity-recency ranking doesn't treat the whole userbase as dormant.
    op.execute("UPDATE users SET last_active_at = created_at WHERE last_active_at IS NULL")

    # ── matches: expiry ───────────────────────────────────────────────────
    _add_column_if_missing('matches', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing('matches', sa.Column(
        'last_activity_at', sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing('matches', sa.Column(
        'expiry_warned_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE matches SET last_activity_at = matched_at WHERE last_activity_at IS NULL")

    # ── interests catalog ─────────────────────────────────────────────────
    if 'interests' not in _existing_tables():
        op.create_table(
            'interests',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('key', sa.String(length=48), nullable=False),
            sa.Column('label', sa.String(length=64), nullable=False),
            sa.Column('label_ne', sa.String(length=64), nullable=True),
            sa.Column('icon', sa.String(length=32), nullable=True),
            sa.Column('category', sa.String(length=32), server_default='other', nullable=False),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('key'),
        )
        op.create_index('ix_interests_key', 'interests', ['key'])

    # ── profile views ─────────────────────────────────────────────────────
    if 'profile_views' not in _existing_tables():
        op.create_table(
            'profile_views',
            sa.Column('id', sa.Uuid(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('viewer_id', sa.Uuid(), nullable=False),
            sa.Column('viewed_id', sa.Uuid(), nullable=False),
            sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('view_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
            sa.Column('notified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
            sa.ForeignKeyConstraint(['viewer_id'], ['users.id']),
            sa.ForeignKeyConstraint(['viewed_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('viewer_id', 'viewed_id', name='uq_profile_view_pair'),
        )
        op.create_index('ix_profile_views_viewer_id', 'profile_views', ['viewer_id'])
        op.create_index('ix_profile_views_viewed_id', 'profile_views', ['viewed_id'])

    # ── DATA: every character is a real partner now, not a practice coach ──
    op.execute("UPDATE saathi_sessions SET companion_mode = 'dating' "
               "WHERE companion_mode = 'practice'")
    op.execute("UPDATE saathi_characters SET companion_enabled = true, "
               "system_prompt_template_id = 'milan_companion_v2'")


def downgrade() -> None:
    op.execute("UPDATE saathi_sessions SET companion_mode = 'practice' "
               "WHERE companion_mode = 'dating'")
    op.drop_index('ix_profile_views_viewed_id', table_name='profile_views')
    op.drop_index('ix_profile_views_viewer_id', table_name='profile_views')
    op.drop_table('profile_views')
    op.drop_index('ix_interests_key', table_name='interests')
    op.drop_table('interests')
    op.drop_column('matches', 'expiry_warned_at')
    op.drop_column('matches', 'last_activity_at')
    op.drop_column('matches', 'expires_at')
    op.drop_index('ix_users_deleted_at', table_name='users')
    op.drop_column('users', 'last_active_at')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'trust_score')
    op.drop_column('profiles', 'interview_answers')
    op.drop_column('messages', 'media_duration_ms')
    op.drop_column('messages', 'media_type')
    op.drop_column('saathi_memory_items', 'last_recalled_at')
    op.drop_column('saathi_sessions', 'deferred_reply_body')
    op.drop_column('saathi_sessions', 'deferred_reply_at')
    op.drop_column('saathi_sessions', 'awaiting_user_reply')
    op.drop_column('saathi_sessions', 'summary_upto_message_at')
    op.drop_column('saathi_sessions', 'rolling_summary')
    op.drop_column('saathi_sessions', 'user_style')
    op.drop_column('saathi_characters', 'hometown')
    op.drop_column('saathi_characters', 'birthday')
    op.drop_column('saathi_characters', 'age')
    op.drop_column('saathi_characters', 'persona_bible')
