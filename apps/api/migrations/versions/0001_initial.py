"""Create GOAG identity, RBAC, device, and audit tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.DateTime(timezone=True)
    op.create_table("companies", sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("timezone", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", now, nullable=False))
    op.create_table("users", sa.Column("id", uuid, primary_key=True), sa.Column("auth_subject", sa.String(255), unique=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("display_name", sa.String(200), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", now, nullable=False))
    op.create_table("memberships", sa.Column("id", uuid, primary_key=True), sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False), sa.Column("user_id", uuid, sa.ForeignKey("users.id"), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("created_at", now, nullable=False), sa.UniqueConstraint("company_id", "user_id", name="uq_membership_company_user"))
    op.create_index("ix_memberships_company_id", "memberships", ["company_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_table("roles", sa.Column("id", uuid, primary_key=True), sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False), sa.Column("code", sa.String(64), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("protected", sa.Boolean, nullable=False), sa.UniqueConstraint("company_id", "code", name="uq_role_company_code"))
    op.create_index("ix_roles_company_id", "roles", ["company_id"])
    op.create_table("permissions", sa.Column("code", sa.String(100), primary_key=True), sa.Column("description", sa.Text, nullable=False))
    op.create_table("membership_roles", sa.Column("membership_id", uuid, sa.ForeignKey("memberships.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", uuid, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True), sa.UniqueConstraint("membership_id", "role_id", name="uq_membership_role"))
    op.create_table("role_permissions", sa.Column("role_id", uuid, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True), sa.Column("permission_code", sa.String(100), sa.ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True), sa.UniqueConstraint("role_id", "permission_code", name="uq_role_permission"))
    op.create_table("registered_devices", sa.Column("id", uuid, primary_key=True), sa.Column("membership_id", uuid, sa.ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False), sa.Column("device_id_hash", sa.String(128), nullable=False), sa.Column("registered_at", now, nullable=False), sa.Column("last_seen_at", now), sa.Column("revoked_at", now))
    op.create_index("ix_registered_devices_membership_id", "registered_devices", ["membership_id"])
    op.create_index("uq_registered_device_active_membership", "registered_devices", ["membership_id"], unique=True, postgresql_where=sa.text("revoked_at IS NULL"))
    op.create_table("audit_events", sa.Column("id", uuid, primary_key=True), sa.Column("company_id", uuid, sa.ForeignKey("companies.id"), nullable=False), sa.Column("actor_membership_id", uuid, sa.ForeignKey("memberships.id")), sa.Column("action", sa.String(100), nullable=False), sa.Column("entity_type", sa.String(100), nullable=False), sa.Column("entity_id", sa.String(100), nullable=False), sa.Column("before_data", postgresql.JSONB), sa.Column("after_data", postgresql.JSONB), sa.Column("reason", sa.Text), sa.Column("correlation_id", sa.String(100)), sa.Column("created_at", now, nullable=False))
    op.create_index("ix_audit_events_company_id", "audit_events", ["company_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("registered_devices")
    op.drop_table("role_permissions")
    op.drop_table("membership_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("companies")
