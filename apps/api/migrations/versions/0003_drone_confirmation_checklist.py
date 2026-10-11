"""Add the drone confirmation checklist."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_drone_checklist"
down_revision: str | None = "0002_inventory_production"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("drones", sa.Column("confirmation_checklist", postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("drones", "confirmation_checklist")
