"""§14 unified companions + swipe economy + payments phase 1

Revision ID: d8a1f2b3c4d5
Revises: c5d9e4f12a78
Create Date: 2026-09-02

- users: is_ai, ai_character_id, saathi_intro_accepted_at, saathi_terms_version,
  include_ai_in_discovery
- profiles: language identity (primary_script, languages, dialect,
  mother_tongue, speech_markers) + search fields (hometown, education,
  height_cm, diet, smoking, drinking, hidden_fields, prompts)
- saathi_sessions: match_id (companions live in the normal inbox)
- matches: kind (human|companion)
- swipes: note, is_rewound, seen_by_target + new swipe_quotas, boosts,
  top_picks tables
- payments: payment_submissions, payment_qr_codes, payment_audit_logs
"""
import sqlalchemy as sa
from alembic import op

revision = 'd8a1f2b3c4d5'
down_revision = 'c5d9e4f12a78'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_ai', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('users', sa.Column('ai_character_id', sa.Uuid(), sa.ForeignKey('saathi_characters.id'), nullable=True))
    op.add_column('users', sa.Column('saathi_intro_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('saathi_terms_version', sa.String(16), nullable=True))
    op.add_column('users', sa.Column('include_ai_in_discovery', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    for name, col in [
        ('primary_script', sa.String(16)),
        ('dialect', sa.String(48)),
        ('mother_tongue', sa.String(48)),
        ('hometown', sa.String(120)),
        ('education', sa.String(120)),
        ('diet', sa.String(24)),
        ('smoking', sa.String(24)),
        ('drinking', sa.String(24)),
    ]:
        op.add_column('profiles', sa.Column(name, col, nullable=True))
    for name in ['languages', 'speech_markers', 'hidden_fields', 'prompts']:
        op.add_column('profiles', sa.Column(name, sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False))
    op.add_column('profiles', sa.Column('height_cm', sa.Integer(), nullable=True))

    op.add_column('saathi_sessions', sa.Column('match_id', sa.Uuid(), sa.ForeignKey('matches.id'), nullable=True))
    op.create_index('ix_saathi_sessions_match_id', 'saathi_sessions', ['match_id'])
    op.add_column('matches', sa.Column('kind', sa.String(16), server_default='human', nullable=False))

    op.add_column('swipes', sa.Column('note', sa.String(140), nullable=True))
    op.add_column('swipes', sa.Column('is_rewound', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('swipes', sa.Column('seen_by_target', sa.Boolean(), server_default=sa.text('false'), nullable=False))

    op.create_table(
        'swipe_quotas',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('day_key', sa.String(10), nullable=False),
        sa.Column('likes_used', sa.Integer(), server_default='0', nullable=False),
        sa.Column('superlikes_used', sa.Integer(), server_default='0', nullable=False),
        sa.Column('rewinds_used', sa.Integer(), server_default='0', nullable=False),
        sa.UniqueConstraint('user_id', 'day_key', name='uq_quota_day'),
    )

    op.create_table(
        'boosts',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('kind', sa.String(16), server_default='boost', nullable=False),
        sa.Column('multiplier', sa.Float(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(24), server_default='tier_grant', nullable=False),
    )

    op.create_table(
        'top_picks',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('candidate_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('day_key', sa.String(10), nullable=False),
        sa.Column('score', sa.Float(), server_default='0', nullable=False),
        sa.Column('reason', sa.String(200), nullable=True),
    )

    op.create_table(
        'payment_submissions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('tier', sa.String(16), nullable=False),
        sa.Column('amount_npr', sa.Integer(), nullable=False),
        sa.Column('method', sa.String(16), nullable=False),
        sa.Column('reference_id', sa.String(120), nullable=False, index=True),
        sa.Column('screenshot_url', sa.String(512), nullable=True),
        sa.Column('screenshot_hash', sa.String(64), nullable=True, index=True),
        sa.Column('note', sa.String(500), nullable=True),
        sa.Column('status', sa.String(16), server_default='pending', nullable=False),
        sa.Column('fraud_flags', sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.String(300), nullable=True),
    )

    op.create_table(
        'payment_qr_codes',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('method', sa.String(16), nullable=False, unique=True),
        sa.Column('image_url', sa.String(512), nullable=False),
        sa.Column('account_label', sa.String(120), nullable=True),
        sa.Column('instructions', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    )

    op.create_table(
        'payment_audit_logs',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submission_id', sa.Uuid(), sa.ForeignKey('payment_submissions.id'), nullable=False, index=True),
        sa.Column('admin_id', sa.Uuid(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(24), nullable=False),
        sa.Column('detail', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    for table in ('payment_audit_logs', 'payment_qr_codes', 'payment_submissions',
                  'top_picks', 'boosts', 'swipe_quotas'):
        op.drop_table(table)
    op.drop_column('swipes', 'seen_by_target')
    op.drop_column('swipes', 'is_rewound')
    op.drop_column('swipes', 'note')
    op.drop_column('matches', 'kind')
    op.drop_index('ix_saathi_sessions_match_id', table_name='saathi_sessions')
    op.drop_column('saathi_sessions', 'match_id')
    for col in ['height_cm', 'prompts', 'hidden_fields', 'drinking', 'smoking',
                'diet', 'education', 'hometown', 'speech_markers', 'mother_tongue',
                'dialect', 'languages', 'primary_script']:
        op.drop_column('profiles', col)
    op.drop_column('users', 'include_ai_in_discovery')
    op.drop_column('users', 'saathi_terms_version')
    op.drop_column('users', 'saathi_intro_accepted_at')
    op.drop_column('users', 'ai_character_id')
    op.drop_column('users', 'is_ai')
