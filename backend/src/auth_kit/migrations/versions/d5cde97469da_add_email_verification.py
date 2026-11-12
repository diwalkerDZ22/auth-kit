"""add email verification"""
from alembic import op
import sqlalchemy as sa

revision = "d5cde97469da"
down_revision = "acd18f9696b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOT NULL + server_default : PostgreSQL remplit les lignes existantes, pas besoin de 3 temps
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Les comptes déjà présents sont considérés comme vérifiés (à adapter si tu préfères les forcer à se vérifier)
    op.execute("UPDATE users SET is_verified = true")

    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("purpose IN ('signup', 'login')", name="ck_email_verifications_purpose"),
    )
    op.create_index("ix_email_verifications_id", "email_verifications", ["id"])
    op.create_index("ix_email_verifications_user_id", "email_verifications", ["user_id"])
    op.create_index(
        "ix_email_verifications_token_hash", "email_verifications", ["token_hash"], unique=True
    )

    # Supabase : empêche l'accès via l'API REST publique (PostgreSQL uniquement)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE email_verifications ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("email_verifications")  # supprime aussi ses index
    op.drop_column("users", "is_verified")