"""unique constraints: match pair, ai_character_id

Revision ID: e9f2a3b4c5d6
Revises: d8a1f2b3c4d5
Create Date: 2026-09-02
"""
import sqlalchemy as sa
from alembic import op

revision = 'e9f2a3b4c5d6'
down_revision = 'd8a1f2b3c4d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # de-dupe existing pairs first (keep earliest) so the constraint applies
    op.execute("""
        DELETE FROM matches m USING matches keep
        WHERE m.user_a_id = keep.user_a_id AND m.user_b_id = keep.user_b_id
          AND m.created_at > keep.created_at
    """)
    op.create_unique_constraint('uq_match_pair', 'matches',
                                ['user_a_id', 'user_b_id'])
    op.execute("""
        DELETE FROM users a USING users b
        WHERE a.ai_character_id = b.ai_character_id
          AND a.ai_character_id IS NOT NULL
          AND a.created_at > b.created_at
    """)
    op.create_unique_constraint('uq_users_ai_character', 'users', ['ai_character_id'])


def downgrade() -> None:
    op.drop_constraint('uq_users_ai_character', 'users', type_='unique')
    op.drop_constraint('uq_match_pair', 'matches', type_='unique')
