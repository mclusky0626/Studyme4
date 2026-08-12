"""Add locally stored image memories.

Revision ID: 20260812_0002
Revises: 20260812_0001
Create Date: 2026-08-12
"""

from alembic import op

from app.db.models import ImageMemory

revision = "20260812_0002"
down_revision = "20260812_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    ImageMemory.__table__.create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    ImageMemory.__table__.drop(bind=op.get_bind(), checkfirst=True)
