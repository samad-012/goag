"""Add geofenced attendance records."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_attendance"
down_revision: str | None = "0006_production_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.DateTime(timezone=True)
    op.create_table(
        "attendance_records",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("membership_id", uuid, sa.ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="present"),
        sa.Column("late", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("check_in_at", now, nullable=False),
        sa.Column("check_out_at", now, nullable=True),
        sa.Column("check_in_latitude", sa.Float(), nullable=False),
        sa.Column("check_in_longitude", sa.Float(), nullable=False),
        sa.Column("check_in_accuracy_m", sa.Float(), nullable=False),
        sa.Column("check_in_distance_m", sa.Float(), nullable=False),
        sa.Column("check_out_latitude", sa.Float(), nullable=True),
        sa.Column("check_out_longitude", sa.Float(), nullable=True),
        sa.Column("check_out_accuracy_m", sa.Float(), nullable=True),
        sa.Column("check_out_distance_m", sa.Float(), nullable=True),
        sa.Column("device_id_hash", sa.String(128), nullable=False),
        sa.Column("corrected_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=True),
        sa.Column("correction_reason", sa.Text(), nullable=True),
        sa.Column("created_at", now, nullable=False),
        sa.Column("updated_at", now, nullable=False),
        sa.UniqueConstraint("membership_id", "work_date", name="uq_attendance_membership_work_date"),
    )
    op.create_index("ix_attendance_records_company_id", "attendance_records", ["company_id"])
    op.create_index("ix_attendance_records_membership_id", "attendance_records", ["membership_id"])
    op.create_index("ix_attendance_records_status", "attendance_records", ["status"])


def downgrade() -> None:
    op.drop_table("attendance_records")
