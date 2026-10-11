from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from .db import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    auth_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="invited")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("company_id", "user_id", name="uq_membership_company_user"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped[User] = relationship()
    company: Mapped[Company] = relationship()


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_role_company_code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(100))
    protected: Mapped[bool] = mapped_column(Boolean, default=False)


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), primary_key=True)
    description: Mapped[str] = mapped_column(Text)


class MembershipRole(Base):
    __tablename__ = "membership_roles"
    __table_args__ = (UniqueConstraint("membership_id", "role_id", name="uq_membership_role"),)

    membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_code", name="uq_role_permission"),)

    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True)


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"
    __table_args__ = (
        Index(
            "uq_registered_device_active_membership",
            "membership_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
            sqlite_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), index=True)
    device_id_hash: Mapped[str] = mapped_column(String(128))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("membership_id", "work_date", name="uq_attendance_membership_work_date"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(32), default="present", index=True)
    late: Mapped[bool] = mapped_column(Boolean, default=False)
    check_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    check_in_latitude: Mapped[float] = mapped_column(Float)
    check_in_longitude: Mapped[float] = mapped_column(Float)
    check_in_accuracy_m: Mapped[float] = mapped_column(Float)
    check_in_distance_m: Mapped[float] = mapped_column(Float)
    check_out_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    check_out_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_id_hash: Mapped[str] = mapped_column(String(128))
    corrected_by_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True)
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class AttendanceException(Base):
    __tablename__ = "attendance_exceptions"
    __table_args__ = (UniqueConstraint("membership_id", "work_date", name="uq_attendance_exception_membership_work_date"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id", ondelete="CASCADE"), index=True)
    work_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="approved", index=True)
    approved_by_membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id"), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    actor_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(100))
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class MailboxConnection(Base):
    __tablename__ = "mailbox_connections"
    __table_args__ = (UniqueConstraint("company_id", name="uq_mailbox_connection_company"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="google_gmail")
    mailbox_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="not_connected")
    refresh_token_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    connected_by_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_state_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    oauth_state_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class ComponentCatalog(Base):
    __tablename__ = "component_catalog"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_component_catalog_company_code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    minimum_stock: Mapped[int] = mapped_column(Integer, default=0)
    storage_location: Mapped[str] = mapped_column(String(200), default="")
    remarks: Mapped[str] = mapped_column(Text, default="")
    serialized: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class DroneModel(Base):
    __tablename__ = "drone_models"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_drone_model_company_code"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class InventoryUnit(Base):
    __tablename__ = "inventory_units"
    __table_args__ = (
        Index("ix_inventory_units_component_status", "component_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    component_id: Mapped[UUID] = mapped_column(ForeignKey("component_catalog.id"), index=True)
    serial_number: Mapped[str | None] = mapped_column(String(150), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="in_stock")
    location: Mapped[str] = mapped_column(String(128), default="store")
    condition: Mapped[str] = mapped_column(String(32), default="good")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Drone(Base):
    __tablename__ = "drones"
    __table_args__ = (UniqueConstraint("company_id", "serial_number", name="uq_drone_company_serial"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    drone_model_id: Mapped[UUID | None] = mapped_column(ForeignKey("drone_models.id"), nullable=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id"))
    confirmation_checklist: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ComponentRequest(Base):
    __tablename__ = "component_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    drone_id: Mapped[UUID] = mapped_column(ForeignKey("drones.id"), index=True)
    requested_by_membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ComponentRequestItem(Base):
    __tablename__ = "component_request_items"
    __table_args__ = (UniqueConstraint("request_id", "component_id", name="uq_component_request_item"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("component_requests.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[UUID] = mapped_column(ForeignKey("component_catalog.id"), index=True)
    requested_quantity: Mapped[int] = mapped_column(Integer)
    issued_quantity: Mapped[int] = mapped_column(Integer, default=0)
    pending_quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="pending")


class ComponentIssue(Base):
    __tablename__ = "component_issues"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("component_requests.id"), index=True)
    issued_by_membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id"))
    approved_by_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="issued")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ComponentIssueLine(Base):
    __tablename__ = "component_issue_lines"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    issue_id: Mapped[UUID] = mapped_column(ForeignKey("component_issues.id", ondelete="CASCADE"), index=True)
    request_item_id: Mapped[UUID] = mapped_column(ForeignKey("component_request_items.id"), index=True)
    inventory_unit_id: Mapped[UUID | None] = mapped_column(ForeignKey("inventory_units.id"), nullable=True)
    substituted_component_id: Mapped[UUID | None] = mapped_column(ForeignKey("component_catalog.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)


class ComponentInstallation(Base):
    __tablename__ = "component_installations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    drone_id: Mapped[UUID] = mapped_column(ForeignKey("drones.id"), index=True)
    inventory_unit_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_units.id"), index=True)
    issue_line_id: Mapped[UUID | None] = mapped_column(ForeignKey("component_issue_lines.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(32))
    performed_by_membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id"))
    approved_by_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True)
    replacement_for_id: Mapped[UUID | None] = mapped_column(ForeignKey("component_installations.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ProductionTask(Base):
    __tablename__ = "production_tasks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), index=True)
    drone_id: Mapped[UUID] = mapped_column(ForeignKey("drones.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    assigned_to_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True, index=True)
    created_by_membership_id: Mapped[UUID] = mapped_column(ForeignKey("memberships.id"))
    completed_by_membership_id: Mapped[UUID | None] = mapped_column(ForeignKey("memberships.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
