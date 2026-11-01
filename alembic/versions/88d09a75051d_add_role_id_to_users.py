"""add role_id to users"""

from alembic import op
import sqlalchemy as sa

revision = "88d09a75051d"
down_revision = "97f7f827c086"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing users must be populated before making the column NOT NULL.
    op.add_column(
        "users",
        sa.Column("role_id", sa.Integer(), nullable=True),
    )

    # Assign existing users to the default role.
    op.execute(
        """
        UPDATE users
        SET role_id = (
            SELECT id
            FROM roles
            WHERE name = 'user'
            LIMIT 1
        )
        WHERE role_id IS NULL
        """
    )

    op.alter_column(
        "users",
        "role_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_users_role_id_roles",
        "users",
        "roles",
        ["role_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_users_role_id_roles",
        "users",
        type_="foreignkey",
    )
    op.drop_column("users", "role_id")