"""Create inventory and production workflow tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_inventory_production"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.DateTime(timezone=True)

    op.create_table(
        "component_catalog",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("serialized", sa.Boolean, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", now, nullable=False),
        sa.UniqueConstraint("company_id", "code", name="uq_component_catalog_company_code"),
    )
    op.create_index("ix_component_catalog_company_id", "component_catalog", ["company_id"])

    op.create_table(
        "inventory_units",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("component_id", uuid, sa.ForeignKey("component_catalog.id"), nullable=False),
        sa.Column("serial_number", sa.String(150), unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("location", sa.String(32), nullable=False),
        sa.Column("condition", sa.String(32), nullable=False),
        sa.Column("created_at", now, nullable=False),
    )
    op.create_index("ix_inventory_units_company_id", "inventory_units", ["company_id"])
    op.create_index("ix_inventory_units_component_id", "inventory_units", ["component_id"])
    op.create_index("ix_inventory_units_component_status", "inventory_units", ["component_id", "status"])

    op.create_table(
        "drones",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("serial_number", sa.String(150)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=False),
        sa.Column("confirmed_at", now),
        sa.Column("confirmed_by_membership_id", uuid, sa.ForeignKey("memberships.id")),
        sa.Column("created_at", now, nullable=False),
        sa.UniqueConstraint("company_id", "serial_number", name="uq_drone_company_serial"),
    )
    op.create_index("ix_drones_company_id", "drones", ["company_id"])
    op.create_index("ix_drones_status", "drones", ["status"])

    op.create_table(
        "component_requests",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("drone_id", uuid, sa.ForeignKey("drones.id"), nullable=False),
        sa.Column("requested_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rejection_reason", sa.Text),
        sa.Column("cancellation_reason", sa.Text),
        sa.Column("created_at", now, nullable=False),
    )
    op.create_index("ix_component_requests_company_id", "component_requests", ["company_id"])
    op.create_index("ix_component_requests_drone_id", "component_requests", ["drone_id"])
    op.create_index("ix_component_requests_status", "component_requests", ["status"])

    op.create_table(
        "component_request_items",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("request_id", uuid, sa.ForeignKey("component_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_id", uuid, sa.ForeignKey("component_catalog.id"), nullable=False),
        sa.Column("requested_quantity", sa.Integer, nullable=False),
        sa.Column("issued_quantity", sa.Integer, nullable=False),
        sa.Column("pending_quantity", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.UniqueConstraint("request_id", "component_id", name="uq_component_request_item"),
    )
    op.create_index("ix_component_request_items_request_id", "component_request_items", ["request_id"])
    op.create_index("ix_component_request_items_component_id", "component_request_items", ["component_id"])

    op.create_table(
        "component_issues",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("request_id", uuid, sa.ForeignKey("component_requests.id"), nullable=False),
        sa.Column("issued_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=False),
        sa.Column("approved_by_membership_id", uuid, sa.ForeignKey("memberships.id")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", now, nullable=False),
    )
    op.create_index("ix_component_issues_company_id", "component_issues", ["company_id"])
    op.create_index("ix_component_issues_request_id", "component_issues", ["request_id"])

    op.create_table(
        "component_issue_lines",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("issue_id", uuid, sa.ForeignKey("component_issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_item_id", uuid, sa.ForeignKey("component_request_items.id"), nullable=False),
        sa.Column("inventory_unit_id", uuid, sa.ForeignKey("inventory_units.id")),
        sa.Column("substituted_component_id", uuid, sa.ForeignKey("component_catalog.id")),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_component_issue_line_quantity_positive"),
    )
    op.create_index("ix_component_issue_lines_issue_id", "component_issue_lines", ["issue_id"])
    op.create_index("ix_component_issue_lines_request_item_id", "component_issue_lines", ["request_item_id"])

    op.create_table(
        "component_installations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("drone_id", uuid, sa.ForeignKey("drones.id"), nullable=False),
        sa.Column("inventory_unit_id", uuid, sa.ForeignKey("inventory_units.id"), nullable=False),
        sa.Column("issue_line_id", uuid, sa.ForeignKey("component_issue_lines.id")),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("performed_by_membership_id", uuid, sa.ForeignKey("memberships.id"), nullable=False),
        sa.Column("approved_by_membership_id", uuid, sa.ForeignKey("memberships.id")),
        sa.Column("replacement_for_id", uuid, sa.ForeignKey("component_installations.id")),
        sa.Column("reason", sa.Text),
        sa.Column("occurred_at", now, nullable=False),
    )
    op.create_index("ix_component_installations_company_id", "component_installations", ["company_id"])
    op.create_index("ix_component_installations_drone_id", "component_installations", ["drone_id"])
    op.create_index("ix_component_installations_inventory_unit_id", "component_installations", ["inventory_unit_id"])


def downgrade() -> None:
    op.drop_table("component_installations")
    op.drop_table("component_issue_lines")
    op.drop_table("component_issues")
    op.drop_table("component_request_items")
    op.drop_table("component_requests")
    op.drop_table("drones")
    op.drop_table("inventory_units")
    op.drop_table("component_catalog")
