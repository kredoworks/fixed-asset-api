"""Initial schema with verification system

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create assets table
    op.create_table(
        'assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_assets_id', 'assets', ['id'], unique=False)
    op.create_index('ix_assets_asset_code', 'assets', ['asset_code'], unique=True)

    # Create verification_cycles table
    op.create_table(
        'verification_cycles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tag', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_verification_cycles_id', 'verification_cycles', ['id'], unique=False)
    op.create_index('ix_verification_cycles_tag', 'verification_cycles', ['tag'], unique=True)

    # Create asset_verifications table
    op.create_table(
        'asset_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('cycle_id', sa.Integer(), nullable=False),
        sa.Column('performed_by', sa.String(100), nullable=True),
        sa.Column('source', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('condition', sa.String(20), nullable=True),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lng', sa.Float(), nullable=True),
        sa.Column('photos', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('override_of_verification_id', sa.Integer(), nullable=True),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cycle_id'], ['verification_cycles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['override_of_verification_id'], ['asset_verifications.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_asset_verifications_id', 'asset_verifications', ['id'], unique=False)
    op.create_index('ix_asset_verifications_asset_id', 'asset_verifications', ['asset_id'], unique=False)
    op.create_index('ix_asset_verifications_cycle_id', 'asset_verifications', ['cycle_id'], unique=False)
    # Composite index for efficient asset+cycle lookups (spec requirement)
    op.create_index('ix_asset_cycle', 'asset_verifications', ['asset_id', 'cycle_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_asset_cycle', table_name='asset_verifications')
    op.drop_index('ix_asset_verifications_cycle_id', table_name='asset_verifications')
    op.drop_index('ix_asset_verifications_asset_id', table_name='asset_verifications')
    op.drop_index('ix_asset_verifications_id', table_name='asset_verifications')
    op.drop_table('asset_verifications')

    op.drop_index('ix_verification_cycles_tag', table_name='verification_cycles')
    op.drop_index('ix_verification_cycles_id', table_name='verification_cycles')
    op.drop_table('verification_cycles')

    op.drop_index('ix_assets_asset_code', table_name='assets')
    op.drop_index('ix_assets_id', table_name='assets')
    op.drop_table('assets')
