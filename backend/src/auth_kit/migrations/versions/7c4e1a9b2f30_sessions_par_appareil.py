"""sessions par appareil (table user_sessions, suppression de users.refresh_token)

Revision ID: 7c4e1a9b2f30
Revises: d6a33616f033
Create Date: 2026-11-12 10:00:00.000000

Les refresh tokens existants ne sont pas repris : chaque utilisateur se reconnecte une fois.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c4e1a9b2f30'
down_revision: Union[str, Sequence[str], None] = 'd6a33616f033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("previous_token_hash", sa.String(64), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_previous_token_hash", "user_sessions", ["previous_token_hash"])

    # Supabase : empêche l'accès via l'API REST publique (PostgreSQL uniquement)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY")

    # Le refresh token en clair n'est plus stocké
    with op.batch_alter_table("users") as batch:
        batch.drop_column("refresh_token")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("refresh_token", sa.String(), nullable=True))
    op.drop_table("user_sessions")   # supprime aussi ses index
