import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..dependencies import current_db, current_membership, granted_permissions
from ..models import (
    AttendanceRecord,
    AuditEvent,
    ComponentCatalog,
    ComponentInstallation,
    ComponentRequest,
    ComponentRequestItem,
    Drone,
    InventoryUnit,
    Membership,
    ProductionTask,
    User,
)
from ..schemas import DashboardAuditEventResponse, DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


ACTIVITY_LABELS: dict[str, tuple[str, str]] = {
    "members.user_created": ("Team member added", "Added"),
    "members.auth_linked": ("Team member connected", "Connected"),
    "device.reset": ("Registered device reset", "Reset"),
    "inventory.component_created": ("Component catalog item added", "Added"),
    "inventory.unit_received": ("Component received into stock", "Received"),
    "inventory.unit_serial_assigned": ("Component serial recorded", "Recorded"),
    "inventory.component_request_created": ("Component request submitted", "Pending"),
    "inventory.components_issued": ("Components issued", "Issued"),
    "inventory.component_request_rejected": ("Component request rejected", "Rejected"),
    "inventory.component_request_cancelled": ("Remaining quantity cancelled", "Cancelled"),
    "drone.created": ("Drone record created", "Created"),
    "drone.confirmed": ("Drone confirmed", "Confirmed"),
    "drone.reopened": ("Drone reopened for correction", "Reopened"),
    "production.task_created": ("Production task created", "Created"),
    "production.task_updated": ("Production task updated", "Updated"),
    "production.component_install": ("Component installed", "Installed"),
    "production.component_remove": ("Component removed", "Removed"),
    "production.component_return": ("Component returned to store", "Returned"),
    "production.component_replace": ("Component replaced", "Replaced"),
    "production.component_damage": ("Component marked damaged", "Damaged"),
    "production.component_action_approved": ("Component action approved", "Approved"),
    "attendance.checked_in": ("Attendance checked in", "Present"),
    "attendance.checked_out": ("Attendance checked out", "Checked out"),
    "attendance.corrected": ("Attendance corrected", "Corrected"),
    "attendance.exception_approved": ("Off-site attendance approved", "Approved"),
    "email.message_sent": ("Mailbox message sent", "Sent"),
    "email.inbox_listed": ("Mailbox viewed", "Viewed"),
    "email.thread_read": ("Mailbox thread opened", "Opened"),
}


def _activity_projection(db: Session, event: AuditEvent) -> DashboardAuditEventResponse:
    action_label, status_label = ACTIVITY_LABELS.get(event.action, ("Operational record updated", "Updated"))
    after = event.after_data or {}
    subject: str | None = None

    if event.entity_type == "user":
        subject = str(after.get("display_name") or after.get("email") or "Team member")
    elif event.entity_type == "drone":
        subject = str(after.get("serial_number") or "Drone serial pending")
    elif event.entity_type == "component_catalog":
        code = after.get("code")
        name = after.get("name")
        subject = " · ".join(str(value) for value in (code, name) if value) or "Component catalog"
    elif event.entity_type == "inventory_unit":
        subject = str(after.get("serial_number") or "Component unit awaiting serial")
    elif event.entity_type == "component_request":
        request = db.get(ComponentRequest, event.entity_id)
        if request:
            drone = db.get(Drone, request.drone_id)
            subject = f"Request for {drone.serial_number}" if drone and drone.serial_number else "Component request"
    elif event.entity_type == "production_task":
        subject = str(after.get("title") or "Production task")
    elif event.entity_type == "component_installation":
        installation = db.get(ComponentInstallation, event.entity_id)
        if installation:
            drone = db.get(Drone, installation.drone_id)
            unit = db.get(InventoryUnit, installation.inventory_unit_id)
            component = db.get(ComponentCatalog, unit.component_id) if unit else None
            part = component.code if component else "Component"
            drone_label = drone.serial_number if drone and drone.serial_number else "drone serial pending"
            subject = f"{part} · {drone_label}"
    elif event.entity_type == "attendance":
        member = db.execute(
            select(User.display_name).join(Membership, Membership.user_id == User.id).where(Membership.id == event.actor_membership_id)
        ).scalar_one_or_none()
        subject = member or "Team attendance"
    elif event.action == "email.message_sent":
        subject = str(after.get("subject") or after.get("to") or "Mailbox message")

    return DashboardAuditEventResponse(
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        action_label=action_label,
        subject=subject,
        status_label=status_label,
        created_at=event.created_at,
    )


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    membership: Membership = Depends(current_membership),
    db: Session = Depends(current_db),
) -> DashboardSummaryResponse:
    settings = get_settings()
    if settings.app_env == "test" and settings.goag_test_proxy_delay_ms > 0:
        time.sleep(settings.goag_test_proxy_delay_ms / 1000)

    permissions = granted_permissions(membership, db)
    today = datetime.now(UTC).date()
    last_30_days = today - timedelta(days=30)

    own_attendance = db.scalar(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.membership_id == membership.id,
            AttendanceRecord.work_date >= last_30_days,
        )
    )
    today_attendance = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.membership_id == membership.id,
            AttendanceRecord.work_date == today,
        )
    )

    summary: dict[str, int | str | None | list[DashboardAuditEventResponse]] = {
        "my_attendance_days_last_30": int(own_attendance or 0),
        "my_attendance_today_status": today_attendance.status if today_attendance else None,
        "recent_audit_events": [],
    }

    if "attendance.read_all" in permissions:
        summary["company_attendance_days_last_30"] = int(
            db.scalar(
                select(func.count(AttendanceRecord.id)).where(
                    AttendanceRecord.company_id == membership.company_id,
                    AttendanceRecord.work_date >= last_30_days,
                )
            )
            or 0
        )

    if "inventory.read" in permissions:
        summary["inventory_in_stock"] = int(
            db.scalar(
                select(func.count(InventoryUnit.id)).where(
                    InventoryUnit.company_id == membership.company_id,
                    InventoryUnit.status == "in_stock",
                )
            )
            or 0
        )
        summary["inventory_issued"] = int(
            db.scalar(
                select(func.count(InventoryUnit.id)).where(
                    InventoryUnit.company_id == membership.company_id,
                    InventoryUnit.status.in_(["issued", "installed"]),
                )
            )
            or 0
        )

    if "request.read_all" in permissions or "request.create" in permissions:
        request_query = select(func.count(ComponentRequest.id)).where(
            ComponentRequest.company_id == membership.company_id,
            ComponentRequest.status.in_(["pending", "partially_issued"]),
        )
        quantity_query = select(func.coalesce(func.sum(ComponentRequestItem.pending_quantity), 0)).join(
            ComponentRequest, ComponentRequest.id == ComponentRequestItem.request_id
        ).where(
            ComponentRequest.company_id == membership.company_id,
            ComponentRequest.status.in_(["pending", "partially_issued"]),
        )
        if "request.read_all" not in permissions:
            request_query = request_query.where(ComponentRequest.requested_by_membership_id == membership.id)
            quantity_query = quantity_query.where(ComponentRequest.requested_by_membership_id == membership.id)
        summary["pending_component_requests"] = int(db.scalar(request_query) or 0)
        summary["backordered_quantity"] = int(db.scalar(quantity_query) or 0)

    if "drone.read" in permissions or "drone.create" in permissions:
        summary["drones_in_production"] = int(
            db.scalar(
                select(func.count(Drone.id)).where(
                    Drone.company_id == membership.company_id,
                    Drone.status == "draft",
                )
            )
            or 0
        )
        summary["confirmed_drones"] = int(
            db.scalar(
                select(func.count(Drone.id)).where(
                    Drone.company_id == membership.company_id,
                    Drone.status == "confirmed",
                )
            )
            or 0
        )

    if "assignment.manage" in permissions or "drone.read" in permissions:
        task_query = select(func.count(ProductionTask.id)).where(
            ProductionTask.company_id == membership.company_id,
            ProductionTask.status != "completed",
        )
        if "assignment.manage" not in permissions:
            task_query = task_query.where(ProductionTask.assigned_to_membership_id == membership.id)
        summary["open_production_tasks"] = int(db.scalar(task_query) or 0)

    if "members.manage" in permissions:
        audit_rows = db.scalars(
            select(AuditEvent)
            .where(AuditEvent.company_id == membership.company_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(8)
        ).all()
        summary["recent_audit_events"] = [_activity_projection(db, event) for event in audit_rows]

    return DashboardSummaryResponse(**summary)
