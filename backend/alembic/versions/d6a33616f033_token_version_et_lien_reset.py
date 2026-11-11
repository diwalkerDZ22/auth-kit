"""token_version et lien reset

Revision ID: d6a33616f033
Revises: 15113d760132
Create Date: 2026-11-11 22:20:08.406320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6a33616f033'
down_revision: Union[str, Sequence[str], None] = '15113d760132'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CK = "ck_email_verifications_purpose"


def _set_purposes(purposes: str) -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite ne relit pas les CHECK : la table est recréée sans l'ancienne contrainte
        with op.batch_alter_table("email_verifications", recreate="always") as batch:
            batch.create_check_constraint(_CK, f"purpose IN ({purposes})")
    else:
        op.drop_constraint(_CK, "email_verifications", type_="check")
        op.create_check_constraint(_CK, "email_verifications", f"purpose IN ({purposes})")


def upgrade() -> None:
    """Upgrade schema."""
    # NOT NULL + server_default : les comptes existants démarrent à 0
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )
    _set_purposes("'signup', 'login', 'reset'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM email_verifications WHERE purpose = 'reset'")
    _set_purposes("'signup', 'login'")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
