"""changement de la table EmailVerification pour accompagner la verification au login sur la meme page

Revision ID: 0bb842af0ea9
Revises: d5cde97469da
Create Date: 2026-11-05 12:26:01.976319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bb842af0ea9'
down_revision: Union[str, Sequence[str], None] = 'd5cde97469da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "email_verifications",
        sa.Column("attempt_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "email_verifications",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("email_verifications", "approved_at")
    op.drop_column("email_verifications", "attempt_hash")
