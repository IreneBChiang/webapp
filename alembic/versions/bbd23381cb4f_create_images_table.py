"""create images table

Revision ID: bbd23381cb4f
Revises: 3c7d9c2b1a01
Create Date: 2025-10-22 20:06:09.925857

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bbd23381cb4f'
down_revision = '3c7d9c2b1a01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "images",
        sa.Column("image_id", sa.Integer, primary_key=True, autoincrement=True, nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),   # ← 跟 products.id 一樣用 BigInteger
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("date_created", sa.DateTime(timezone=True),
                 server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("s3_bucket_path", sa.String(1024), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )


def downgrade():
    op.drop_table('images')
