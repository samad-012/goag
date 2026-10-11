from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..dependencies import current_db, current_membership, has_permission, require_permissions
from ..models import (
    ComponentCatalog,
    ComponentInstallation,
    ComponentIssueLine,
    ComponentRequest,
    ComponentRequestItem,
    Drone,
    DroneModel,
    InventoryUnit,
    Membership,
    MembershipRole,
    ProductionTask,
    Role,
    User,
)
from ..schemas import (
    ComponentActionCreate,
    ComponentInstallationResponse,
    DroneConfirmationRequest,
    DroneConfirmationResponse,
    DroneCreate,
    DroneModelCreate,
    DroneModelResponse,
    DroneResponse,
    ProductionAssigneeResponse,
    ProductionTaskCreate,
    ProductionTaskResponse,
    ProductionTaskUpdate,
    ReopenDroneRequest,
)

router = APIRouter(prefix="/production", tags=["production"])


def _installation_response(db: Session, installation: ComponentInstallation) -> ComponentInstallationResponse:
    drone = db.get(Drone, installation.drone_id)
    unit = db.get(InventoryUnit, installation.inventory_unit_id)
    component = db.get(ComponentCatalog, unit.component_id) if unit else None
    return ComponentInstallationResponse(
        id=installation.id,
        drone_id=installation.drone_id,
        drone_serial_number=drone.serial_number if drone else None,
        inventory_unit_id=installation.inventory_unit_id,
        component_code=component.code if component else None,
        component_name=component.name if component else None,
        component_serial_number=unit.serial_number if unit else None,
        action=installation.action,
        performed_by_membership_id=installation.performed_by_membership_id,
        approved_by_membership_id=installation.approved_by_membership_id,
        replacement_for_id=installation.replacement_for_id,
        reason=installation.reason,
        occurred_at=installation.occurred_at,
    )


def _task_response(db: Session, task: ProductionTask) -> ProductionTaskResponse:
    drone = db.get(Drone, task.drone_id)
    assignee_name = None
    if task.assigned_to_membership_id:
        assignee_name = db.scalar(
            select(User.display_name)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.id == task.assigned_to_membership_id)
        )
    return ProductionTaskResponse(
        id=task.id,
        drone_id=task.drone_id,
        drone_serial_number=drone.serial_number if drone else None,
        title=task.title,
        status=task.status,
        assigned_to_membership_id=task.assigned_to_membership_id,
        assignee_display_name=assignee_name,
        created_by_membership_id=task.created_by_membership_id,
        completed_by_membership_id=task.completed_by_membership_id,
        notes=task.notes,
        completed_at=task.completed_at,
        created_at=task.created_at,
    )


@router.post("/drones", response_model=DroneResponse, status_code=status.HTTP_201_CREATED)
def create_drone(
    payload: DroneCreate,
    membership: Membership = Depends(require_permissions("drone.create")),
    db: Session = Depends(current_db),
) -> DroneResponse:
    if payload.drone_model_id:
        model = db.scalar(
            select(DroneModel).where(
                DroneModel.id == payload.drone_model_id,
                DroneModel.company_id == membership.company_id,
                DroneModel.status == "active",
            )
        )
        if not model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone model not found")
    if payload.serial_number:
        existing = db.scalar(
            select(Drone).where(
                Drone.company_id == membership.company_id,
                Drone.serial_number == payload.serial_number,
            )
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Drone serial number already exists")

    drone = Drone(
        company_id=membership.company_id,
        drone_model_id=payload.drone_model_id,
        serial_number=payload.serial_number,
        notes=payload.notes,
        created_by_membership_id=membership.id,
    )
    db.add(drone)
    db.flush()
    record_audit(
        db,
        membership=membership,
        action="drone.created",
        entity_type="drone",
        entity_id=drone.id,
        after={"serial_number": drone.serial_number, "status": drone.status},
    )
    db.commit()
    db.refresh(drone)
    return DroneResponse.model_validate(drone)


@router.get("/drone-models", response_model=list[DroneModelResponse])
def list_drone_models(
    membership: Membership = Depends(require_permissions("drone.read")),
    db: Session = Depends(current_db),
) -> list[DroneModelResponse]:
    models = db.scalars(
        select(DroneModel)
        .where(DroneModel.company_id == membership.company_id, DroneModel.status == "active")
        .order_by(DroneModel.code)
    ).all()
    return [DroneModelResponse.model_validate(model) for model in models]


@router.get("/assignees", response_model=list[ProductionAssigneeResponse])
def list_production_assignees(
    membership: Membership = Depends(require_permissions("assignment.manage")),
    db: Session = Depends(current_db),
) -> list[ProductionAssigneeResponse]:
    rows = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .join(MembershipRole, MembershipRole.membership_id == Membership.id)
        .join(Role, Role.id == MembershipRole.role_id)
        .where(
            Membership.company_id == membership.company_id,
            Membership.status == "active",
            User.status == "active",
            Role.code == "TECHNICIAN",
        )
        .order_by(User.display_name)
    ).all()
    return [ProductionAssigneeResponse(membership_id=member.id, user_id=user.id, display_name=user.display_name, email=user.email) for member, user in rows]


@router.post("/drone-models", response_model=DroneModelResponse, status_code=status.HTTP_201_CREATED)
def create_drone_model(
    payload: DroneModelCreate,
    membership: Membership = Depends(require_permissions("drone.create")),
    db: Session = Depends(current_db),
) -> DroneModelResponse:
    existing = db.scalar(
        select(DroneModel).where(
            DroneModel.company_id == membership.company_id,
            DroneModel.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Drone model code already exists")

    model = DroneModel(company_id=membership.company_id, code=payload.code, name=payload.name)
    db.add(model)
    db.flush()
    record_audit(
        db,
        membership=membership,
        action="production.drone_model_created",
        entity_type="drone_model",
        entity_id=model.id,
        after={"code": model.code, "name": model.name},
    )
    db.commit()
    db.refresh(model)
    return DroneModelResponse.model_validate(model)


@router.get("/drones", response_model=list[DroneResponse])
def list_drones(
    membership: Membership = Depends(require_permissions("drone.read")),
    db: Session = Depends(current_db),
) -> list[DroneResponse]:
    drones = db.scalars(
        select(Drone)
        .where(Drone.company_id == membership.company_id)
        .order_by(Drone.created_at.desc())
    ).all()
    return [DroneResponse.model_validate(drone) for drone in drones]


@router.get("/component-installations", response_model=list[ComponentInstallationResponse])
def list_component_installations(
    membership: Membership = Depends(require_permissions("drone.read")),
    db: Session = Depends(current_db),
) -> list[ComponentInstallationResponse]:
    installations = db.scalars(
        select(ComponentInstallation)
        .where(ComponentInstallation.company_id == membership.company_id)
        .order_by(ComponentInstallation.occurred_at.desc())
    ).all()
    return [_installation_response(db, installation) for installation in installations]


@router.get("/tasks", response_model=list[ProductionTaskResponse])
def list_production_tasks(
    membership: Membership = Depends(require_permissions("drone.read")),
    db: Session = Depends(current_db),
) -> list[ProductionTaskResponse]:
    query = select(ProductionTask).where(ProductionTask.company_id == membership.company_id)
    if not has_permission(membership, db, "assignment.manage"):
        if not has_permission(membership, db, "assignment.update_own"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing production task permission")
        query = query.where(ProductionTask.assigned_to_membership_id == membership.id)
    tasks = db.scalars(query.order_by(ProductionTask.created_at.desc())).all()
    return [_task_response(db, task) for task in tasks]


@router.post("/drones/{drone_id}/tasks", response_model=ProductionTaskResponse, status_code=status.HTTP_201_CREATED)
def create_production_task(
    drone_id: UUID,
    payload: ProductionTaskCreate,
    membership: Membership = Depends(require_permissions("assignment.manage")),
    db: Session = Depends(current_db),
) -> ProductionTaskResponse:
    drone = db.scalar(select(Drone).where(Drone.id == drone_id, Drone.company_id == membership.company_id))
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    if payload.assigned_to_membership_id:
        assignee = db.scalar(
            select(Membership)
            .join(MembershipRole, MembershipRole.membership_id == Membership.id)
            .join(Role, Role.id == MembershipRole.role_id)
            .where(
                Membership.id == payload.assigned_to_membership_id,
                Membership.company_id == membership.company_id,
                Membership.status == "active",
                Role.code == "TECHNICIAN",
            )
        )
        if not assignee:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Assigned user must be an active technician")
    task = ProductionTask(
        company_id=membership.company_id,
        drone_id=drone.id,
        title=payload.title,
        assigned_to_membership_id=payload.assigned_to_membership_id,
        created_by_membership_id=membership.id,
        notes=payload.notes,
    )
    db.add(task)
    db.flush()
    record_audit(db, membership=membership, action="production.task_created", entity_type="production_task", entity_id=task.id, after={"drone_id": str(drone.id), "title": task.title, "assigned_to_membership_id": str(task.assigned_to_membership_id) if task.assigned_to_membership_id else None})
    db.commit()
    db.refresh(task)
    return _task_response(db, task)


@router.patch("/tasks/{task_id}", response_model=ProductionTaskResponse)
def update_production_task(
    task_id: UUID,
    payload: ProductionTaskUpdate,
    membership: Membership = Depends(current_membership),
    db: Session = Depends(current_db),
) -> ProductionTaskResponse:
    task = db.scalar(select(ProductionTask).where(ProductionTask.id == task_id, ProductionTask.company_id == membership.company_id))
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Production task not found")
    can_manage = has_permission(membership, db, "assignment.manage")
    can_update_own = has_permission(membership, db, "assignment.update_own")
    if not can_manage and (not can_update_own or task.assigned_to_membership_id != membership.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned technician or a production manager can update this task")
    before = {"status": task.status, "notes": task.notes}
    task.status = payload.status
    task.notes = payload.notes
    if payload.status == "completed":
        task.completed_at = datetime.now(UTC)
        task.completed_by_membership_id = membership.id
    else:
        task.completed_at = None
        task.completed_by_membership_id = None
    record_audit(db, membership=membership, action="production.task_updated", entity_type="production_task", entity_id=task.id, before=before, after={"status": task.status, "notes": task.notes})
    db.commit()
    db.refresh(task)
    return _task_response(db, task)


def _validate_issue_line(db: Session, issue_line_id: UUID | None, drone: Drone, inventory_unit_id: UUID) -> None:
    if issue_line_id is None:
        return
    issue_line = db.scalar(
        select(ComponentIssueLine)
        .join(ComponentRequestItem, ComponentRequestItem.id == ComponentIssueLine.request_item_id)
        .join(ComponentRequest, ComponentRequest.id == ComponentRequestItem.request_id)
        .where(
            ComponentIssueLine.id == issue_line_id,
            ComponentIssueLine.inventory_unit_id == inventory_unit_id,
            ComponentRequest.drone_id == drone.id,
        )
    )
    if not issue_line:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Issue line does not belong to this drone")


@router.post("/drones/{drone_id}/components", response_model=ComponentInstallationResponse, status_code=status.HTTP_201_CREATED)
def component_action(
    drone_id: UUID,
    payload: ComponentActionCreate,
    membership: Membership = Depends(current_membership),
    db: Session = Depends(current_db),
) -> ComponentInstallationResponse:
    drone = db.scalar(select(Drone).where(Drone.id == drone_id, Drone.company_id == membership.company_id))
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    if drone.status == "confirmed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Confirmed drone is locked; reopen it before changing components")

    permission_by_action = {
        "install": "component.install",
        "remove": "component.install",
        "replace": "component.install",
        "return": "inventory.return_receive",
        "damage": "inventory.damage",
    }
    required_permission = permission_by_action[payload.action]
    if not has_permission(membership, db, required_permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission")

    unit = db.scalar(
        select(InventoryUnit).where(
            InventoryUnit.id == payload.inventory_unit_id,
            InventoryUnit.company_id == membership.company_id,
        )
    )
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory unit not found")
    if payload.action in {"install", "replace"} and not unit.serial_number:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Component serial number is required before installation")
    _validate_issue_line(db, payload.issue_line_id, drone, unit.id)

    replacement_for_id = payload.replacement_for_id
    if payload.action == "install":
        if unit.status not in {"issued", "removed", "in_stock"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory unit cannot be installed in its current state")
        unit.status = "installed"
        unit.location = f"drone:{drone.id}"
    elif payload.action == "remove":
        if unit.status != "installed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an installed component can be removed")
        unit.status = "removed"
        unit.location = "technician"
    elif payload.action == "return":
        if unit.status not in {"removed", "issued"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only removed or issued components can be returned")
        unit.status = "in_stock"
        unit.location = "store"
    elif payload.action == "damage":
        unit.status = "damaged"
        unit.location = "store"
    elif payload.action == "replace":
        if not replacement_for_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="replacement_for_id is required")
        old_installation = db.scalar(
            select(ComponentInstallation).where(
                ComponentInstallation.id == replacement_for_id,
                ComponentInstallation.drone_id == drone.id,
                ComponentInstallation.action == "install",
            )
        )
        if not old_installation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installed component to replace was not found")
        old_unit = db.get(InventoryUnit, old_installation.inventory_unit_id)
        if not old_unit or old_unit.status != "installed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The component to replace is not currently installed")
        old_unit.status = "removed"
        old_unit.location = "technician"
        db.add(
            ComponentInstallation(
                company_id=membership.company_id,
                drone_id=drone.id,
                inventory_unit_id=old_unit.id,
                action="remove",
                performed_by_membership_id=membership.id,
                approved_by_membership_id=membership.id if has_permission(membership, db, "completion.confirm") else None,
                replacement_for_id=old_installation.id,
                reason=payload.reason or "Component replaced",
            )
        )
        unit.status = "installed"
        unit.location = f"drone:{drone.id}"

    approval_permission = "completion.confirm" if payload.action in {"install", "remove", "replace"} else required_permission
    installation = ComponentInstallation(
        company_id=membership.company_id,
        drone_id=drone.id,
        inventory_unit_id=unit.id,
        issue_line_id=payload.issue_line_id,
        action=payload.action,
        performed_by_membership_id=membership.id,
        approved_by_membership_id=membership.id if has_permission(membership, db, approval_permission) else None,
        replacement_for_id=replacement_for_id,
        reason=payload.reason,
    )
    db.add(installation)
    db.flush()
    record_audit(
        db,
        membership=membership,
        action=f"production.component_{payload.action}",
        entity_type="component_installation",
        entity_id=installation.id,
        after={"drone_id": str(drone.id), "inventory_unit_id": str(unit.id), "action": payload.action, "approved": installation.approved_by_membership_id is not None},
        reason=payload.reason,
    )
    db.commit()
    db.refresh(installation)
    return _installation_response(db, installation)


@router.post("/component-installations/{installation_id}/approve", response_model=ComponentInstallationResponse)
def approve_component_action(
    installation_id: UUID,
    membership: Membership = Depends(require_permissions("completion.confirm")),
    db: Session = Depends(current_db),
) -> ComponentInstallationResponse:
    installation = db.scalar(
        select(ComponentInstallation).where(
            ComponentInstallation.id == installation_id,
            ComponentInstallation.company_id == membership.company_id,
        )
    )
    if not installation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component action not found")
    if installation.approved_by_membership_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Component action is already approved")
    installation.approved_by_membership_id = membership.id
    record_audit(db, membership=membership, action="production.component_action_approved", entity_type="component_installation", entity_id=installation.id, after={"approved_by_membership_id": str(membership.id)})
    db.commit()
    db.refresh(installation)
    return _installation_response(db, installation)


@router.post("/drones/{drone_id}/reopen", response_model=DroneResponse)
def reopen_drone(
    drone_id: UUID,
    payload: ReopenDroneRequest,
    membership: Membership = Depends(require_permissions("completion.confirm")),
    db: Session = Depends(current_db),
) -> DroneResponse:
    drone = db.scalar(select(Drone).where(Drone.id == drone_id, Drone.company_id == membership.company_id))
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    if drone.status != "confirmed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a confirmed drone can be reopened")
    drone.status = "draft"
    drone.confirmation_checklist = None
    drone.confirmed_at = None
    drone.confirmed_by_membership_id = None
    record_audit(db, membership=membership, action="drone.reopened", entity_type="drone", entity_id=drone.id, reason=payload.reason, after={"status": drone.status})
    db.commit()
    db.refresh(drone)
    return DroneResponse.model_validate(drone)


REQUIRED_CONFIRMATION_CHECKLIST = {
    "required_components_installed",
    "component_quantities_correct",
    "serial_numbers_recorded",
    "production_tasks_completed",
    "component_issues_resolved",
    "drone_serial_exists",
    "quality_checklist_completed",
}


@router.post("/drones/{drone_id}/confirm", response_model=DroneConfirmationResponse)
def confirm_drone(
    drone_id: UUID,
    payload: DroneConfirmationRequest,
    membership: Membership = Depends(require_permissions("completion.confirm")),
    db: Session = Depends(current_db),
) -> DroneConfirmationResponse:
    drone = db.scalar(select(Drone).where(Drone.id == drone_id, Drone.company_id == membership.company_id))
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    if drone.status == "confirmed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Drone is already confirmed")
    missing_checks = sorted(key for key in REQUIRED_CONFIRMATION_CHECKLIST if payload.checklist.get(key) is not True)
    if missing_checks:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Checklist items are incomplete: {', '.join(missing_checks)}")
    if not drone.serial_number:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Drone serial number is required")

    requests = db.scalars(select(ComponentRequest).where(ComponentRequest.drone_id == drone.id)).all()
    if any(request.status not in {"fulfilled", "cancelled"} for request in requests):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="All component requests must be fulfilled or cancelled before confirmation")
    request_items = db.scalars(
        select(ComponentRequestItem).where(ComponentRequestItem.request_id.in_([request.id for request in requests]))
    ).all() if requests else []
    cancelled_request_ids = {request.id for request in requests if request.status == "cancelled"}
    if any(item.pending_quantity != 0 and item.request_id not in cancelled_request_ids for item in request_items):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pending component quantities remain")

    issue_lines = db.scalars(
        select(ComponentIssueLine)
        .join(ComponentRequestItem, ComponentRequestItem.id == ComponentIssueLine.request_item_id)
        .join(ComponentRequest, ComponentRequest.id == ComponentRequestItem.request_id)
        .where(ComponentRequest.drone_id == drone.id)
    ).all()
    if any(line.inventory_unit_id is None for line in issue_lines):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Every issued component must have an inventory unit")
    unit_ids = [line.inventory_unit_id for line in issue_lines if line.inventory_unit_id]
    units = db.scalars(select(InventoryUnit).where(InventoryUnit.id.in_(unit_ids))).all() if unit_ids else []
    if any(not unit.serial_number or unit.status != "installed" for unit in units):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Every installed component needs a serial number")
    installations = db.scalars(
        select(ComponentInstallation).where(ComponentInstallation.drone_id == drone.id).order_by(ComponentInstallation.occurred_at, ComponentInstallation.id)
    ).all()
    latest = {}
    for installation in installations:
        latest[installation.inventory_unit_id] = installation
    if any(latest.get(unit_id) is None or latest[unit_id].action not in {"install", "replace"} or latest[unit_id].approved_by_membership_id is None for unit_id in unit_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Every component installation must be approved")

    from datetime import UTC, datetime

    drone.status = "confirmed"
    drone.confirmation_checklist = payload.checklist
    drone.confirmed_at = datetime.now(UTC)
    drone.confirmed_by_membership_id = membership.id
    record_audit(db, membership=membership, action="drone.confirmed", entity_type="drone", entity_id=drone.id, after={"status": drone.status, "checklist": payload.checklist})
    db.commit()
    db.refresh(drone)
    return DroneConfirmationResponse.model_validate(drone)
