"""Add production task tracking."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_production_tasks"
down_revision: str | None = "0005_remove_bom_feature"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.DateTime(timezone=True)
    op.create_table(
        "production_tasks",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("drone_id", uuid, sa.ForeignKey("drones.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("assigned_to_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=True),
        sa.Column("created_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=False),
        sa.Column("completed_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", now, nullable=True),
        sa.Column("created_at", now, nullable=False),
    )
    op.create_index("ix_production_tasks_company_id", "production_tasks", ["company_id"])
    op.create_index("ix_production_tasks_drone_id", "production_tasks", ["drone_id"])
    op.create_index("ix_production_tasks_status", "production_tasks", ["status"])
    op.create_index("ix_production_tasks_assigned_to_membership_id", "production_tasks", ["assigned_to_membership_id"])


def downgrade() -> None:
    op.drop_table("production_tasks")
