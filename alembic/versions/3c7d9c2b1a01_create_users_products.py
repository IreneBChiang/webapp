"""create users and products

Revision ID: 3c7d9c2b1a01
Revises: 05ab2104be64
Create Date: 2025-09-22 02:42:21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c7d9c2b1a01'
down_revision = '05ab2104be64'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('account_created', sa.DateTime(timezone=True), server_default=sa.text('utc_timestamp()'), nullable=False),
        sa.Column('account_updated', sa.DateTime(timezone=True), server_default=sa.text('utc_timestamp()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    op.create_table('products',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=2000), nullable=True),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('manufacturer', sa.String(length=200), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('date_added', sa.DateTime(timezone=True), server_default=sa.text('utc_timestamp()'), nullable=False),
        sa.Column('date_last_updated', sa.DateTime(timezone=True), server_default=sa.text('utc_timestamp()'), nullable=False),
        sa.Column('owner_user_id', sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index('idx_products_owner', 'products', ['owner_user_id'], unique=False)

    # add check constraints for quantity
    op.create_check_constraint('ck_products_quantity_nonneg', 'products', 'quantity >= 0')
    op.create_check_constraint('ck_products_quantity_max', 'products', 'quantity <= 100')


def downgrade():
    op.drop_constraint('ck_products_quantity_max', 'products', type_='check')
    op.drop_constraint('ck_products_quantity_nonneg', 'products', type_='check')
    op.drop_index('idx_products_owner', table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
