
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import Identity, get_identity
from app.db import Base
from app.dependencies import current_db
from app.main import app
from app.models import (
    AuditEvent,
    Company,
    ComponentInstallation,
    ComponentIssueLine,
    ComponentRequest,
    InventoryUnit,
    Membership,
    MembershipRole,
    Permission,
    RegisteredDevice,
    Role,
    RolePermission,
    User,
)

engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)


def override_db():
    with TestingSession() as db:
        yield db


def make_identity(subject: str = "md-subject") -> Identity:
    return Identity(subject=subject, email="md@goag.example")


app.dependency_overrides[current_db] = override_db
app.dependency_overrides[get_identity] = make_identity
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


def setup_data() -> None:
    with TestingSession.begin() as db:
        company = Company(name="GOAG", timezone="Asia/Kolkata", status="active")
        user = User(auth_subject="md-subject", email="md@goag.example", display_name="Managing Director", status="active")
        db.add_all([company, user])
        db.flush()
        membership = Membership(company_id=company.id, user_id=user.id, status="active")
        db.add(membership)
        role = Role(company_id=company.id, code="MANAGING_DIRECTOR", name="Managing Director", protected=True)
        db.add(role)
        permission = Permission(code="members.manage", description="Manage members")
        db.add(permission)
        db.flush()
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
        db.add(RolePermission(role_id=role.id, permission_code=permission.code))


def grant_md_permissions(*permission_codes: str) -> None:
    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        for code in permission_codes:
            permission = Permission(code=code, description=f"Test permission {code}")
            db.add(permission)
            db.flush()
            db.add(RolePermission(role_id=role.id, permission_code=permission.code))


def test_health() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_current_user_requires_membership_and_returns_permissions() -> None:
    setup_data()
    response = client.get("/api/v1/me")
    assert response.status_code == 200
    assert response.json()["role_codes"] == ["MANAGING_DIRECTOR"]
    assert response.json()["permission_codes"] == ["members.manage"]


def test_every_active_user_can_read_own_attendance_and_dashboard_summary() -> None:
    setup_data()
    attendance = client.get("/api/v1/attendance/me")
    assert attendance.status_code == 200
    assert attendance.json() == []

    summary = client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["my_attendance_days_last_30"] == 0
    assert summary.json()["my_attendance_today_status"] is None


def test_invited_user_is_linked_to_supabase_subject_on_first_request() -> None:
    setup_data()
    with TestingSession.begin() as db:
        company = db.scalar(select(Company).where(Company.name == "GOAG"))
        assert company is not None
        invited = User(auth_subject=None, email="invited@goag.example", display_name="Invited user", status="invited")
        db.add(invited)
        db.flush()
        db.add(Membership(company_id=company.id, user_id=invited.id, status="active"))

    original_identity = app.dependency_overrides[get_identity]
    app.dependency_overrides[get_identity] = lambda: Identity(subject="invited-subject", email="invited@goag.example")
    try:
        response = client.get("/api/v1/me")
    finally:
        app.dependency_overrides[get_identity] = original_identity

    assert response.status_code == 200
    with TestingSession() as db:
        linked = db.scalar(select(User).where(User.email == "invited@goag.example"))
        assert linked is not None
        assert linked.auth_subject == "invited-subject"
        assert linked.status == "active"
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "members.auth_linked")) is not None


def test_shared_mailbox_status_is_rbac_protected_and_reports_configuration() -> None:
    setup_data()
    forbidden = client.get("/api/v1/email/status")
    assert forbidden.status_code == 403

    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        permission = Permission(code="mailbox.read", description="View the shared GOAG mailbox")
        db.add(permission)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_code=permission.code))

    response = client.get("/api/v1/email/status")
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["provider"] == "google_gmail"


def test_shared_mailbox_oauth_start_requires_management_and_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_data()
    forbidden = client.get("/api/v1/email/oauth/start")
    assert forbidden.status_code == 403

    for name in (
        "GOAG_GMAIL_CLIENT_ID",
        "GOAG_GMAIL_CLIENT_SECRET",
        "GOAG_GMAIL_REDIRECT_URI",
        "GOAG_GMAIL_TOKEN_ENCRYPTION_KEY",
    ):
        monkeypatch.setenv(name, "")
    from app.config import get_settings

    get_settings.cache_clear()

    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        permission = Permission(code="mailbox.manage", description="Manage the shared GOAG mailbox")
        db.add(permission)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_code=permission.code))

    response = client.get("/api/v1/email/oauth/start")
    assert response.status_code == 503
    assert "credentials" in response.json()["detail"]
    get_settings.cache_clear()


def test_shared_mailbox_inbox_requires_read_permission_and_connection() -> None:
    setup_data()
    assert client.get("/api/v1/email/messages").status_code == 403

    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        permission = Permission(code="mailbox.read", description="View the shared GOAG mailbox")
        db.add(permission)
        db.flush()
        db.add(RolePermission(role_id=role.id, permission_code=permission.code))

    assert client.get("/api/v1/email/messages").status_code == 503
    assert client.get("/api/v1/email/threads/thread-1").status_code == 503


def test_managing_director_can_create_user_and_audit_event_is_written() -> None:
    setup_data()
    response = client.post(
        "/api/v1/admin/users",
        json={"email": "tech@goag.example", "display_name": "Technician", "role_codes": ["MANAGING_DIRECTOR"]},
    )
    assert response.status_code == 201
    assert response.json()["role_codes"] == ["MANAGING_DIRECTOR"]
    with TestingSession() as db:
        assert db.scalar(select(User).where(User.email == "tech@goag.example")) is not None
        event = db.scalar(select(AuditEvent).where(AuditEvent.action == "members.user_created"))
        assert event is not None

    summary = client.get("/api/v1/dashboard/summary")
    assert summary.status_code == 200
    created_event = next(item for item in summary.json()["recent_audit_events"] if item["action"] == "members.user_created")
    assert created_event["action_label"] == "Team member added"
    assert created_event["subject"] == "Technician"
    assert created_event["status_label"] == "Added"


def test_one_device_registration_and_administrator_reset() -> None:
    setup_data()
    from app.config import get_settings

    get_settings.cache_clear()
    get_settings().device_hash_secret = "test-device-secret"
    first = client.post("/api/v1/me/device", json={"device_id": "device-identifier-0001"})
    assert first.status_code == 200
    same = client.post("/api/v1/me/device", json={"device_id": "device-identifier-0001"})
    assert same.status_code == 200
    second = client.post("/api/v1/me/device", json={"device_id": "device-identifier-0002"})
    assert second.status_code == 409
    with TestingSession() as db:
        user_id = db.scalar(select(User.id).where(User.auth_subject == "md-subject"))
    reset = client.post(f"/api/v1/admin/users/{user_id}/device/reset")
    assert reset.status_code == 204
    replacement = client.post("/api/v1/me/device", json={"device_id": "device-identifier-0002"})
    assert replacement.status_code == 200
    with TestingSession() as db:
        assert db.scalar(select(RegisteredDevice).where(RegisteredDevice.revoked_at.is_not(None))) is not None


def test_geofenced_attendance_check_in_out_and_history() -> None:
    setup_data()
    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        for code in ("attendance.check_in", "attendance.read_all", "attendance.correct"):
            permission = Permission(code=code, description=f"Test permission {code}")
            db.add(permission)
            db.flush()
            db.add(RolePermission(role_id=role.id, permission_code=permission.code))

    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.device_hash_secret = "test-device-secret"
    settings.goag_test_worksite_lat = 0
    settings.goag_test_worksite_lon = 0
    settings.goag_test_geofence_radius_m = 150
    settings.goag_max_gps_accuracy_m = 100

    registered = client.post("/api/v1/me/device", json={"device_id": "attendance-device-0001"})
    assert registered.status_code == 200
    payload = {
        "device_id": "attendance-device-0001",
        "latitude": 0,
        "longitude": 0,
        "accuracy_m": 10,
        "gps_denied": False,
    }
    checked_in = client.post("/api/v1/attendance/check-in", json=payload)
    assert checked_in.status_code == 200
    assert checked_in.json()["status"] in {"present", "late"}
    assert client.post("/api/v1/attendance/check-in", json=payload).status_code == 409
    checked_out = client.post("/api/v1/attendance/check-out", json=payload)
    assert checked_out.status_code == 200
    assert checked_out.json()["check_out_at"] is not None
    history = client.get("/api/v1/attendance")
    assert history.status_code == 200
    assert len(history.json()) == 1
    with TestingSession() as db:
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "attendance.checked_in")) is not None
        assert db.scalar(select(AuditEvent).where(AuditEvent.action == "attendance.checked_out")) is not None


def test_manager_approved_offsite_exception_allows_gps_attendance() -> None:
    setup_data()
    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        for code in ("attendance.check_in", "attendance.read_all", "attendance.correct"):
            permission = Permission(code=code, description=f"Test permission {code}")
            db.add(permission)
            db.flush()
            db.add(RolePermission(role_id=role.id, permission_code=permission.code))
        membership_id = db.scalar(select(Membership.id))
        assert membership_id is not None

    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.device_hash_secret = "test-device-secret"
    settings.goag_test_worksite_lat = 0
    settings.goag_test_worksite_lon = 0
    settings.goag_test_geofence_radius_m = 150
    settings.goag_max_gps_accuracy_m = 100

    registered = client.post("/api/v1/me/device", json={"device_id": "offsite-device-0001"})
    assert registered.status_code == 200
    payload = {
        "device_id": "offsite-device-0001",
        "latitude": 1,
        "longitude": 1,
        "accuracy_m": 10,
        "gps_denied": False,
    }
    rejected = client.post("/api/v1/attendance/check-in", json=payload)
    assert rejected.status_code == 422
    approved = client.post(
        "/api/v1/attendance/exceptions",
        json={"membership_id": str(membership_id), "work_date": datetime.now(UTC).date().isoformat(), "reason": "Field work"},
    )
    assert approved.status_code == 201
    allowed = client.post("/api/v1/attendance/check-in", json=payload)
    assert allowed.status_code == 200


def test_create_component_drone_and_component_request() -> None:
    setup_data()
    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        for code in ("inventory.catalog.manage", "drone.create", "request.create"):
            db.add(Permission(code=code, description=f"Test permission {code}"))
            db.flush()
            db.add(RolePermission(role_id=role.id, permission_code=code))

    component = client.post(
        "/api/v1/inventory/components",
        json={"code": "MOTOR-001", "name": "Motor", "category": "propulsion", "serialized": True},
    )
    model = client.post("/api/v1/production/drone-models", json={"code": "10X-PRO", "name": "10X Pro"})
    assert component.status_code == 201
    assert model.status_code == 201

    drone = client.post("/api/v1/production/drones", json={"drone_model_id": model.json()["id"], "serial_number": "DRONE-001"})
    assert drone.status_code == 201

    request = client.post(
        "/api/v1/inventory/component-requests",
        json={
            "drone_id": drone.json()["id"],
            "items": [{"component_id": component.json()["id"], "requested_quantity": 10}],
        },
    )
    assert request.status_code == 201
    assert request.json()["status"] == "pending"
    assert request.json()["drone_serial_number"] == "DRONE-001"
    assert request.json()["items"][0]["component_code"] == "MOTOR-001"
    assert request.json()["items"][0]["component_name"] == "Motor"
    assert request.json()["items"][0]["pending_quantity"] == 10


def test_partial_issue_serial_install_and_confirm_drone() -> None:
    setup_data()
    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        for code in (
            "inventory.catalog.manage",
            "inventory.issue",
            "inventory.substitute",
            "drone.create",
            "drone.read",
            "assignment.manage",
            "request.create",
            "component.install",
            "completion.confirm",
        ):
            db.add(Permission(code=code, description=f"Test permission {code}"))
            db.flush()
            db.add(RolePermission(role_id=role.id, permission_code=code))

    component = client.post(
        "/api/v1/inventory/components",
        json={"code": "FLIGHT-CONTROLLER", "name": "Flight Controller", "category": "avionics"},
    )
    drone = client.post("/api/v1/production/drones", json={"serial_number": "DRONE-FLOW-001"})
    request = client.post(
        "/api/v1/inventory/component-requests",
        json={"drone_id": drone.json()["id"], "items": [{"component_id": component.json()["id"], "requested_quantity": 2}]},
    )
    assert all(response.status_code == 201 for response in (component, drone, request))

    task = client.post(
        f"/api/v1/production/drones/{drone.json()['id']}/tasks",
        json={"title": "Prepare frame assembly"},
    )
    assert task.status_code == 201
    task_update = client.patch(f"/api/v1/production/tasks/{task.json()['id']}", json={"status": "completed"})
    assert task_update.status_code == 200
    assert task_update.json()["status"] == "completed"

    first_issue = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/issue",
        json={"lines": [{"request_item_id": request.json()["items"][0]["id"], "quantity": 1}]},
    )
    assert first_issue.status_code == 201
    assert first_issue.json()["request_status"] == "partially_issued"

    with TestingSession() as db:
        units = db.scalars(select(InventoryUnit).order_by(InventoryUnit.created_at)).all()
        item = db.scalar(select(ComponentIssueLine).where(ComponentIssueLine.issue_id == UUID(first_issue.json()["id"])))
        assert len(units) == 1
        assert item is not None
        first_unit_id = units[0].id

    serial = client.patch(f"/api/v1/inventory/units/{first_unit_id}/serial", json={"serial_number": "FC-0001"})
    assert serial.status_code == 200

    second_issue = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/issue",
        json={"lines": [{"request_item_id": request.json()["items"][0]["id"], "quantity": 1, "serial_numbers": ["FC-0002"]}]},
    )
    assert second_issue.status_code == 201
    assert second_issue.json()["request_status"] == "fulfilled"

    with TestingSession() as db:
        units = db.scalars(select(InventoryUnit).order_by(InventoryUnit.created_at)).all()
        issue_lines = [
            db.get(ComponentIssueLine, UUID(first_issue.json()["issue_line_ids"][0])),
            db.get(ComponentIssueLine, UUID(second_issue.json()["issue_line_ids"][0])),
        ]
        assert len(units) == 2
        assert all(issue_line is not None for issue_line in issue_lines)
        assert units[1].serial_number == "FC-0002"
        second_unit_id = units[1].id

    for unit_id, issue_line in zip((first_unit_id, second_unit_id), issue_lines, strict=True):
        installation = client.post(
            f"/api/v1/production/drones/{drone.json()['id']}/components",
            json={"action": "install", "inventory_unit_id": str(unit_id), "issue_line_id": str(issue_line.id)},
        )
        assert installation.status_code == 201

    installation_history = client.get("/api/v1/production/component-installations")
    assert installation_history.status_code == 200
    assert len(installation_history.json()) == 2

    confirmed = client.post(
        f"/api/v1/production/drones/{drone.json()['id']}/confirm",
        json={
            "checklist": {
                "required_components_installed": True,
                "component_quantities_correct": True,
                "serial_numbers_recorded": True,
                "production_tasks_completed": True,
                "component_issues_resolved": True,
                "drone_serial_exists": True,
                "quality_checklist_completed": True,
            }
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    reopened = client.post(
        f"/api/v1/production/drones/{drone.json()['id']}/reopen",
        json={"reason": "Correct a production record after quality review"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "draft"


def test_opening_inventory_to_confirmed_drone_workflow() -> None:
    """Validate the operational path using existing serialized stock from opening inventory."""
    setup_data()
    with TestingSession.begin() as db:
        role = db.scalar(select(Role).where(Role.code == "MANAGING_DIRECTOR"))
        assert role is not None
        for code in (
            "inventory.catalog.manage",
            "inventory.receive",
            "inventory.issue",
            "drone.create",
            "drone.read",
            "assignment.manage",
            "request.create",
            "component.install",
            "completion.confirm",
        ):
            db.add(Permission(code=code, description=f"Test permission {code}"))
            db.flush()
            db.add(RolePermission(role_id=role.id, permission_code=code))

    component = client.post(
        "/api/v1/inventory/components",
        json={"code": "FC-OPENING", "name": "Flight Controller", "category": "avionics", "serialized": True},
    )
    assert component.status_code == 201

    opening_with_serial = client.post(
        "/api/v1/inventory/units",
        json={"component_id": component.json()["id"], "serial_number": "FC-OPEN-001", "condition": "good", "location": "store"},
    )
    opening_pending_serial = client.post(
        "/api/v1/inventory/units",
        json={"component_id": component.json()["id"], "condition": "good", "location": "store"},
    )
    assert opening_with_serial.status_code == 201
    assert opening_pending_serial.status_code == 201
    assert opening_pending_serial.json()["serial_number"] is None
    assert opening_pending_serial.json()["status"] == "in_stock"

    drone = client.post("/api/v1/production/drones", json={"serial_number": "DRONE-OPENING-001"})
    assert drone.status_code == 201
    drone_id = drone.json()["id"]

    request = client.post(
        "/api/v1/inventory/component-requests",
        json={"drone_id": drone_id, "items": [{"component_id": component.json()["id"], "requested_quantity": 2}]},
    )
    assert request.status_code == 201
    request_item_id = request.json()["items"][0]["id"]

    task = client.post(f"/api/v1/production/drones/{drone_id}/tasks", json={"title": "Assemble flight controller"})
    assert task.status_code == 201

    partial_issue = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/issue",
        json={
            "lines": [
                {
                    "request_item_id": request_item_id,
                    "quantity": 1,
                    "inventory_unit_ids": [opening_pending_serial.json()["id"]],
                }
            ]
        },
    )
    assert partial_issue.status_code == 201
    assert partial_issue.json()["request_status"] == "partially_issued"

    with TestingSession() as db:
        item = db.get(ComponentIssueLine, UUID(partial_issue.json()["issue_line_ids"][0]))
        assert item is not None
        pending_unit_id = item.inventory_unit_id
        assert pending_unit_id == UUID(opening_pending_serial.json()["id"])

    assigned_serial = client.patch(
        f"/api/v1/inventory/units/{pending_unit_id}/serial",
        json={"serial_number": "FC-OPEN-002"},
    )
    assert assigned_serial.status_code == 200

    second_issue = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/issue",
        json={
            "lines": [
                {
                    "request_item_id": request_item_id,
                    "quantity": 1,
                    "inventory_unit_ids": [opening_with_serial.json()["id"]],
                }
            ]
        },
    )
    assert second_issue.status_code == 201
    assert second_issue.json()["request_status"] == "fulfilled"

    task_update = client.patch(f"/api/v1/production/tasks/{task.json()['id']}", json={"status": "completed"})
    assert task_update.status_code == 200

    installation_ids = []
    for issue_line_id, unit_id in (
        (partial_issue.json()["issue_line_ids"][0], pending_unit_id),
        (second_issue.json()["issue_line_ids"][0], UUID(opening_with_serial.json()["id"])),
    ):
        installation = client.post(
            f"/api/v1/production/drones/{drone_id}/components",
            json={"action": "install", "inventory_unit_id": str(unit_id), "issue_line_id": issue_line_id},
        )
        assert installation.status_code == 201
        assert installation.json()["approved_by_membership_id"] is not None
        installation_ids.append(installation.json()["id"])

    confirmed = client.post(
        f"/api/v1/production/drones/{drone_id}/confirm",
        json={
            "checklist": {
                "required_components_installed": True,
                "component_quantities_correct": True,
                "serial_numbers_recorded": True,
                "production_tasks_completed": True,
                "component_issues_resolved": True,
                "drone_serial_exists": True,
                "quality_checklist_completed": True,
            }
        },
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    with TestingSession() as db:
        units = db.scalars(select(InventoryUnit).order_by(InventoryUnit.serial_number)).all()
        assert [(unit.serial_number, unit.status) for unit in units] == [
            ("FC-OPEN-001", "installed"),
            ("FC-OPEN-002", "installed"),
        ]
        assert {event.action for event in db.scalars(select(AuditEvent)).all()} >= {
            "inventory.unit_received",
            "inventory.unit_serial_assigned",
            "inventory.component_request_created",
            "inventory.components_issued",
            "production.component_install",
            "production.task_updated",
            "drone.confirmed",
        }
    assert len(installation_ids) == 2


def test_component_substitution_requires_store_permission_and_is_audited() -> None:
    setup_data()
    grant_md_permissions("inventory.catalog.manage", "inventory.issue", "inventory.substitute", "drone.create", "request.create")

    requested = client.post(
        "/api/v1/inventory/components",
        json={"code": "MOTOR-REQUESTED", "name": "Requested motor", "category": "propulsion"},
    )
    substitute = client.post(
        "/api/v1/inventory/components",
        json={"code": "MOTOR-SUBSTITUTE", "name": "Approved substitute motor", "category": "propulsion"},
    )
    drone = client.post("/api/v1/production/drones", json={"serial_number": "DRONE-SUB-001"})
    assert all(response.status_code == 201 for response in (requested, substitute, drone))

    request = client.post(
        "/api/v1/inventory/component-requests",
        json={"drone_id": drone.json()["id"], "items": [{"component_id": requested.json()["id"], "requested_quantity": 1}]},
    )
    assert request.status_code == 201
    issue = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/issue",
        json={
            "lines": [{
                "request_item_id": request.json()["items"][0]["id"],
                "quantity": 1,
                "serial_numbers": ["MOTOR-SUB-001"],
                "substituted_component_id": substitute.json()["id"],
            }]
        },
    )
    assert issue.status_code == 201
    assert issue.json()["request_status"] == "fulfilled"

    with TestingSession() as db:
        issue_line = db.get(ComponentIssueLine, UUID(issue.json()["issue_line_ids"][0]))
        audit = db.scalar(select(AuditEvent).where(AuditEvent.action == "inventory.components_issued"))
        assert issue_line is not None
        assert issue_line.substituted_component_id == UUID(substitute.json()["id"])
        assert audit is not None
        assert audit.after_data["lines"][0]["substituted_component_id"] == substitute.json()["id"]


def test_component_request_rejection_records_reason_and_audit() -> None:
    setup_data()
    grant_md_permissions("inventory.catalog.manage", "inventory.issue", "drone.create", "request.create")

    component = client.post(
        "/api/v1/inventory/components",
        json={"code": "REJECT-MOTOR", "name": "Rejectable motor", "category": "propulsion"},
    )
    drone = client.post("/api/v1/production/drones", json={"serial_number": "DRONE-REJECT-001"})
    request = client.post(
        "/api/v1/inventory/component-requests",
        json={"drone_id": drone.json()["id"], "items": [{"component_id": component.json()["id"], "requested_quantity": 2}]},
    )
    assert all(response.status_code == 201 for response in (component, drone, request))

    rejected = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/reject",
        json={"reason": "The requested component is not approved for this drone model."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    with TestingSession() as db:
        stored_request = db.get(ComponentRequest, UUID(request.json()["id"]))
        audit = db.scalar(select(AuditEvent).where(AuditEvent.action == "inventory.component_request_rejected"))
        assert stored_request is not None
        assert stored_request.rejection_reason == "The requested component is not approved for this drone model."
        assert audit is not None
        assert audit.reason == stored_request.rejection_reason


def test_completed_drone_can_cancel_remaining_quantity_before_confirmation() -> None:
    setup_data()
    grant_md_permissions(
        "inventory.catalog.manage",
        "inventory.issue",
        "drone.create",
        "drone.read",
        "request.create",
        "component.install",
        "completion.confirm",
        "assignment.manage",
    )

    component = client.post(
        "/api/v1/inventory/components",
        json={"code": "PARTIAL-MOTOR", "name": "Partially available motor", "category": "propulsion"},
    )
    drone = client.post("/api/v1/production/drones", json={"serial_number": "DRONE-CANCEL-001"})
    request = client.post(
        "/api/v1/inventory/component-requests",
        json={"drone_id": drone.json()["id"], "items": [{"component_id": component.json()["id"], "requested_quantity": 2}]},
    )
    assert all(response.status_code == 201 for response in (component, drone, request))

    issue = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/issue",
        json={"lines": [{"request_item_id": request.json()["items"][0]["id"], "quantity": 1, "serial_numbers": ["PARTIAL-001"]}]},
    )
    assert issue.status_code == 201
    task = client.post(f"/api/v1/production/drones/{drone.json()['id']}/tasks", json={"title": "Complete assembly"})
    assert task.status_code == 201
    assert client.patch(f"/api/v1/production/tasks/{task.json()['id']}", json={"status": "completed"}).status_code == 200

    with TestingSession() as db:
        issue_line = db.get(ComponentIssueLine, UUID(issue.json()["issue_line_ids"][0]))
        assert issue_line is not None
        unit_id = issue_line.inventory_unit_id
        assert unit_id is not None

    installation = client.post(
        f"/api/v1/production/drones/{drone.json()['id']}/components",
        json={"action": "install", "inventory_unit_id": str(unit_id), "issue_line_id": issue.json()["issue_line_ids"][0]},
    )
    assert installation.status_code == 201

    cancelled = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/cancel",
        json={"reason": "The drone is complete with the one available unit; the remaining quantity is not needed."},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["items"][0]["pending_quantity"] == 1

    confirmed = client.post(
        f"/api/v1/production/drones/{drone.json()['id']}/confirm",
        json={"checklist": {
            "required_components_installed": True,
            "component_quantities_correct": True,
            "serial_numbers_recorded": True,
            "production_tasks_completed": True,
            "component_issues_resolved": True,
            "drone_serial_exists": True,
            "quality_checklist_completed": True,
        }},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    with TestingSession() as db:
        stored_request = db.get(ComponentRequest, UUID(request.json()["id"]))
        audit = db.scalar(select(AuditEvent).where(AuditEvent.action == "inventory.component_request_cancelled"))
        assert stored_request is not None
        assert stored_request.cancellation_reason is not None
        assert audit is not None
        assert audit.reason == stored_request.cancellation_reason


def test_component_lifecycle_tracks_remove_replace_return_and_damage() -> None:
    setup_data()
    grant_md_permissions(
        "inventory.catalog.manage",
        "inventory.issue",
        "inventory.return_receive",
        "inventory.damage",
        "drone.create",
        "request.create",
        "component.install",
        "completion.confirm",
    )

    component = client.post(
        "/api/v1/inventory/components",
        json={"code": "LIFECYCLE-MOTOR", "name": "Lifecycle motor", "category": "propulsion"},
    )
    drone = client.post("/api/v1/production/drones", json={"serial_number": "DRONE-LIFECYCLE-001"})
    request = client.post(
        "/api/v1/inventory/component-requests",
        json={"drone_id": drone.json()["id"], "items": [{"component_id": component.json()["id"], "requested_quantity": 3}]},
    )
    assert all(response.status_code == 201 for response in (component, drone, request))
    issue = client.post(
        f"/api/v1/inventory/component-requests/{request.json()['id']}/issue",
        json={
            "lines": [{
                "request_item_id": request.json()["items"][0]["id"],
                "quantity": 3,
                "serial_numbers": ["LIFE-001", "LIFE-002", "LIFE-003"],
            }]
        },
    )
    assert issue.status_code == 201
    issue_line_ids = issue.json()["issue_line_ids"]
    unit_ids = issue.json()["inventory_unit_ids"]
    drone_id = drone.json()["id"]

    first_install = client.post(
        f"/api/v1/production/drones/{drone_id}/components",
        json={"action": "install", "inventory_unit_id": unit_ids[0], "issue_line_id": issue_line_ids[0]},
    )
    assert first_install.status_code == 201
    removed = client.post(
        f"/api/v1/production/drones/{drone_id}/components",
        json={"action": "remove", "inventory_unit_id": unit_ids[0], "issue_line_id": issue_line_ids[0], "reason": "Replace during inspection"},
    )
    assert removed.status_code == 201
    returned = client.post(
        f"/api/v1/production/drones/{drone_id}/components",
        json={"action": "return", "inventory_unit_id": unit_ids[0], "issue_line_id": issue_line_ids[0], "reason": "Returned to store"},
    )
    assert returned.status_code == 201

    second_install = client.post(
        f"/api/v1/production/drones/{drone_id}/components",
        json={"action": "install", "inventory_unit_id": unit_ids[1], "issue_line_id": issue_line_ids[1]},
    )
    assert second_install.status_code == 201
    replaced = client.post(
        f"/api/v1/production/drones/{drone_id}/components",
        json={
            "action": "replace",
            "inventory_unit_id": unit_ids[2],
            "issue_line_id": issue_line_ids[2],
            "replacement_for_id": second_install.json()["id"],
            "reason": "Use the replacement motor",
        },
    )
    assert replaced.status_code == 201
    damaged = client.post(
        f"/api/v1/production/drones/{drone_id}/components",
        json={"action": "damage", "inventory_unit_id": unit_ids[2], "reason": "Damaged during bench test"},
    )
    assert damaged.status_code == 201

    with TestingSession() as db:
        units = [db.get(InventoryUnit, UUID(unit_id)) for unit_id in unit_ids]
        actions = db.scalars(select(ComponentInstallation).where(ComponentInstallation.drone_id == UUID(drone_id))).all()
        audit_actions = {event.action for event in db.scalars(select(AuditEvent)).all()}
        assert all(unit is not None for unit in units)
        assert [unit.status for unit in units if unit is not None] == ["in_stock", "removed", "damaged"]
        assert {action.action for action in actions} >= {"install", "remove", "return", "replace", "damage"}
        assert {"production.component_remove", "production.component_replace", "production.component_return", "production.component_damage"} <= audit_actions
        assert replaced.json()["replacement_for_id"] == second_install.json()["id"]
