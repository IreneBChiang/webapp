"""add verification fields

Revision ID: 897b021e0b05
Revises: bbd23381cb4f
Create Date: 2025-11-12 23:21:56.988540

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '897b021e0b05'
down_revision = 'bbd23381cb4f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("verification_token", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("verification_expiry", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_users_verification_token", "users", ["verification_token"])


def downgrade():
    op.drop_constraint("uq_users_verification_token", "users", type_="unique")
    op.drop_column("users", "verification_expiry")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "is_verified")
