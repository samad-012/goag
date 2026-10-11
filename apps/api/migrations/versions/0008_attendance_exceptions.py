"""Add manager-approved attendance exceptions."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_attendance_exceptions"
down_revision: str | None = "0007_attendance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.DateTime(timezone=True)
    op.create_table(
        "attendance_exceptions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("membership_id", uuid, sa.ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="approved"),
        sa.Column("approved_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=False),
        sa.Column("approved_at", now, nullable=False),
        sa.Column("created_at", now, nullable=False),
        sa.UniqueConstraint("membership_id", "work_date", name="uq_attendance_exception_membership_work_date"),
    )
    op.create_index("ix_attendance_exceptions_company_id", "attendance_exceptions", ["company_id"])
    op.create_index("ix_attendance_exceptions_membership_id", "attendance_exceptions", ["membership_id"])
    op.create_index("ix_attendance_exceptions_status", "attendance_exceptions", ["status"])


def downgrade() -> None:
    op.drop_table("attendance_exceptions")
