from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..dependencies import current_db, current_membership, has_permission, require_permissions
from ..models import (
    ComponentCatalog,
    ComponentIssue,
    ComponentIssueLine,
    ComponentRequest,
    ComponentRequestItem,
    Drone,
    InventoryUnit,
    Membership,
    ProductionTask,
)
from ..schemas import (
    ComponentCatalogCreate,
    ComponentCatalogResponse,
    ComponentIssueCreate,
    ComponentIssueResponse,
    ComponentRequestCreate,
    ComponentRequestItemResponse,
    ComponentRequestResponse,
    InventoryUnitCreate,
    InventoryUnitResponse,
    RequestActionReason,
    SerialAssignRequest,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _refresh_request_status(db: Session, request: ComponentRequest) -> None:
    items = db.scalars(select(ComponentRequestItem).where(ComponentRequestItem.request_id == request.id)).all()
    if items and all(item.pending_quantity == 0 for item in items):
        request.status = "fulfilled"
    elif any(item.issued_quantity > 0 for item in items):
        request.status = "partially_issued"
    else:
        request.status = "pending"


def _component_request_response(db: Session, request: ComponentRequest) -> ComponentRequestResponse:
    items = db.scalars(
        select(ComponentRequestItem).where(ComponentRequestItem.request_id == request.id)
    ).all()
    component_ids = {item.component_id for item in items}
    components = {
        component.id: component
        for component in db.scalars(
            select(ComponentCatalog).where(ComponentCatalog.id.in_(component_ids))
        ).all()
    } if component_ids else {}
    drone = db.get(Drone, request.drone_id)
    return ComponentRequestResponse(
        id=request.id,
        drone_id=request.drone_id,
        drone_serial_number=drone.serial_number if drone else None,
        status=request.status,
        items=[
            ComponentRequestItemResponse(
                id=item.id,
                component_id=item.component_id,
                component_code=components[item.component_id].code if item.component_id in components else None,
                component_name=components[item.component_id].name if item.component_id in components else None,
                requested_quantity=item.requested_quantity,
                issued_quantity=item.issued_quantity,
                pending_quantity=item.pending_quantity,
                status=item.status,
            )
            for item in items
        ],
        created_at=request.created_at,
    )


@router.post("/components", response_model=ComponentCatalogResponse, status_code=status.HTTP_201_CREATED)
def create_component(
    payload: ComponentCatalogCreate,
    membership: Membership = Depends(require_permissions("inventory.catalog.manage")),
    db: Session = Depends(current_db),
) -> ComponentCatalogResponse:
    existing = db.scalar(
        select(ComponentCatalog).where(
            ComponentCatalog.company_id == membership.company_id,
            ComponentCatalog.code == payload.code,
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Component code already exists")

    component = ComponentCatalog(company_id=membership.company_id, **payload.model_dump())
    db.add(component)
    db.flush()
    record_audit(
        db,
        membership=membership,
        action="inventory.component_created",
        entity_type="component_catalog",
        entity_id=component.id,
        after={"code": component.code, "name": component.name, "serialized": component.serialized},
    )
    db.commit()
    db.refresh(component)
    return ComponentCatalogResponse.model_validate(component)


@router.get("/components", response_model=list[ComponentCatalogResponse])
def list_components(
    membership: Membership = Depends(require_permissions("inventory.read")),
    db: Session = Depends(current_db),
) -> list[ComponentCatalogResponse]:
    components = db.scalars(
        select(ComponentCatalog)
        .where(ComponentCatalog.company_id == membership.company_id, ComponentCatalog.status == "active")
        .order_by(ComponentCatalog.code)
    ).all()
    return [ComponentCatalogResponse.model_validate(component) for component in components]


@router.post("/units", response_model=InventoryUnitResponse, status_code=status.HTTP_201_CREATED)
def receive_inventory_unit(
    payload: InventoryUnitCreate,
    membership: Membership = Depends(require_permissions("inventory.receive")),
    db: Session = Depends(current_db),
) -> InventoryUnitResponse:
    component = db.scalar(
        select(ComponentCatalog).where(
            ComponentCatalog.id == payload.component_id,
            ComponentCatalog.company_id == membership.company_id,
            ComponentCatalog.status == "active",
        )
    )
    if not component:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    if payload.serial_number and db.scalar(
        select(InventoryUnit).where(InventoryUnit.serial_number == payload.serial_number)
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Component serial number already exists")

    unit = InventoryUnit(company_id=membership.company_id, **payload.model_dump())
    db.add(unit)
    db.flush()
    record_audit(
        db,
        membership=membership,
        action="inventory.unit_received",
        entity_type="inventory_unit",
        entity_id=unit.id,
        after={"component_id": str(unit.component_id), "serial_number": unit.serial_number, "status": unit.status},
    )
    db.commit()
    db.refresh(unit)
    return InventoryUnitResponse.model_validate(unit)


@router.get("/units", response_model=list[InventoryUnitResponse])
def list_inventory_units(
    status_filter: str | None = Query(default=None, alias="status"),
    membership: Membership = Depends(require_permissions("inventory.read")),
    db: Session = Depends(current_db),
) -> list[InventoryUnitResponse]:
    query = select(InventoryUnit).where(InventoryUnit.company_id == membership.company_id)
    if status_filter:
        query = query.where(InventoryUnit.status == status_filter)
    units = db.scalars(query.order_by(InventoryUnit.created_at.desc())).all()
    return [InventoryUnitResponse.model_validate(unit) for unit in units]


@router.patch("/units/{unit_id}/serial", response_model=InventoryUnitResponse)
def assign_inventory_serial(
    unit_id: UUID,
    payload: SerialAssignRequest,
    membership: Membership = Depends(current_membership),
    db: Session = Depends(current_db),
) -> InventoryUnitResponse:
    if not has_permission(membership, db, "inventory.issue") and not has_permission(membership, db, "component.install"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission")
    unit = db.scalar(
        select(InventoryUnit).where(InventoryUnit.id == unit_id, InventoryUnit.company_id == membership.company_id)
    )
    if not unit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory unit not found")
    if unit.status == "installed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Installed component serial cannot be edited")
    existing = db.scalar(select(InventoryUnit).where(InventoryUnit.serial_number == payload.serial_number))
    if existing and existing.id != unit.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Component serial number already exists")
    before = {"serial_number": unit.serial_number}
    unit.serial_number = payload.serial_number
    record_audit(
        db,
        membership=membership,
        action="inventory.unit_serial_assigned",
        entity_type="inventory_unit",
        entity_id=unit.id,
        before=before,
        after={"serial_number": unit.serial_number},
    )
    db.commit()
    db.refresh(unit)
    return InventoryUnitResponse.model_validate(unit)


@router.post("/component-requests", response_model=ComponentRequestResponse, status_code=status.HTTP_201_CREATED)
def create_component_request(
    payload: ComponentRequestCreate,
    membership: Membership = Depends(require_permissions("request.create")),
    db: Session = Depends(current_db),
) -> ComponentRequestResponse:
    drone = db.scalar(
        select(Drone).where(Drone.id == payload.drone_id, Drone.company_id == membership.company_id)
    )
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")

    component_ids = [item.component_id for item in payload.items]
    if len(set(component_ids)) != len(component_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each component may appear once per request")
    components = db.scalars(
        select(ComponentCatalog).where(
            ComponentCatalog.company_id == membership.company_id,
            ComponentCatalog.id.in_(component_ids),
            ComponentCatalog.status == "active",
        )
    ).all()
    if len(components) != len(component_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One or more components were not found")

    request = ComponentRequest(
        company_id=membership.company_id,
        drone_id=drone.id,
        requested_by_membership_id=membership.id,
    )
    db.add(request)
    db.flush()
    for item in payload.items:
        db.add(
            ComponentRequestItem(
                request_id=request.id,
                component_id=item.component_id,
                requested_quantity=item.requested_quantity,
                pending_quantity=item.requested_quantity,
            )
        )
    record_audit(
        db,
        membership=membership,
        action="inventory.component_request_created",
        entity_type="component_request",
        entity_id=request.id,
        after={
            "drone_id": str(drone.id),
            "items": [
                {"component_id": str(item.component_id), "requested_quantity": item.requested_quantity}
                for item in payload.items
            ],
        },
    )
    db.commit()
    return _component_request_response(db, request)


@router.get("/component-requests", response_model=list[ComponentRequestResponse])
def list_component_requests(
    membership: Membership = Depends(require_permissions("request.read_all")),
    db: Session = Depends(current_db),
) -> list[ComponentRequestResponse]:
    requests = db.scalars(
        select(ComponentRequest)
        .where(ComponentRequest.company_id == membership.company_id)
        .order_by(ComponentRequest.created_at.desc())
    ).all()
    return [_component_request_response(db, request) for request in requests]


@router.post("/component-requests/{request_id}/issue", response_model=ComponentIssueResponse, status_code=status.HTTP_201_CREATED)
def issue_components(
    request_id: UUID,
    payload: ComponentIssueCreate,
    membership: Membership = Depends(require_permissions("inventory.issue")),
    db: Session = Depends(current_db),
) -> ComponentIssueResponse:
    request = db.scalar(
        select(ComponentRequest).where(
            ComponentRequest.id == request_id,
            ComponentRequest.company_id == membership.company_id,
        )
    )
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component request not found")
    if request.status in {"fulfilled", "rejected", "partially_rejected", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Component request is not open")

    item_ids = [line.request_item_id for line in payload.lines]
    if len(set(item_ids)) != len(item_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Each request item may be issued once per transaction")
    items = db.scalars(
        select(ComponentRequestItem).where(
            ComponentRequestItem.request_id == request.id,
            ComponentRequestItem.id.in_(item_ids),
        )
    ).all()
    item_map = {item.id: item for item in items}
    if len(item_map) != len(item_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request item not found")

    issue = ComponentIssue(
        company_id=membership.company_id,
        request_id=request.id,
        issued_by_membership_id=membership.id,
        approved_by_membership_id=membership.id,
        notes=payload.notes,
    )
    db.add(issue)
    db.flush()
    issue_line_ids = []
    inventory_unit_ids = []
    audit_lines = []
    for line in payload.lines:
        item = item_map[line.request_item_id]
        if line.quantity > item.pending_quantity:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Issue quantity exceeds pending quantity")
        if line.substituted_component_id:
            if not has_permission(membership, db, "inventory.substitute"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Substitution approval is required")
            substitute = db.scalar(
                select(ComponentCatalog).where(
                    ComponentCatalog.id == line.substituted_component_id,
                    ComponentCatalog.company_id == membership.company_id,
                    ComponentCatalog.status == "active",
                )
            )
            if not substitute:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Substitute component not found")
            expected_component_id = substitute.id
        else:
            expected_component_id = item.component_id

        if line.inventory_unit_ids and len(line.inventory_unit_ids) != line.quantity:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One inventory unit is required per issued serialized quantity")
        if len(set(line.inventory_unit_ids)) != len(line.inventory_unit_ids):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Inventory units cannot repeat")
        if line.inventory_unit_ids and line.serial_numbers:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provide inventory units or serial numbers, not both")
        if line.serial_numbers and len(line.serial_numbers) != line.quantity:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One serial number is required per issued serialized quantity")
        serial_numbers = [serial.strip() for serial in line.serial_numbers]
        if any(not serial for serial in serial_numbers):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Serial numbers cannot be empty")
        if len(set(serial_numbers)) != len(serial_numbers):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Serial numbers cannot repeat")

        units = []
        if line.inventory_unit_ids:
            units = db.scalars(
                select(InventoryUnit).where(
                    InventoryUnit.id.in_(line.inventory_unit_ids),
                    InventoryUnit.company_id == membership.company_id,
                )
            ).all()
            if len(units) != len(line.inventory_unit_ids):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory unit not found")
            if any(unit.component_id != expected_component_id or unit.status != "in_stock" for unit in units):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory unit is not available for issue")
        elif serial_numbers:
            for serial_number in serial_numbers:
                unit = db.scalar(
                    select(InventoryUnit).where(
                        InventoryUnit.serial_number == serial_number,
                        InventoryUnit.company_id == membership.company_id,
                    )
                )
                if unit:
                    if unit.component_id != expected_component_id or unit.status != "in_stock":
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Component serial {serial_number} is not available for issue")
                else:
                    unit = InventoryUnit(
                        company_id=membership.company_id,
                        component_id=expected_component_id,
                        serial_number=serial_number,
                    )
                    db.add(unit)
                    db.flush()
                units.append(unit)
        else:
            for _ in range(line.quantity):
                unit = InventoryUnit(company_id=membership.company_id, component_id=expected_component_id)
                db.add(unit)
                db.flush()
                units.append(unit)

        for unit in units:
            unit.status = "issued"
            unit.location = "technician"
            issue_line = ComponentIssueLine(
                issue_id=issue.id,
                request_item_id=item.id,
                inventory_unit_id=unit.id,
                substituted_component_id=line.substituted_component_id,
                quantity=1,
            )
            db.add(issue_line)
            db.flush()
            issue_line_ids.append(issue_line.id)
            inventory_unit_ids.append(unit.id)
        item.issued_quantity += line.quantity
        item.pending_quantity -= line.quantity
        item.status = "fulfilled" if item.pending_quantity == 0 else "partially_issued"
        audit_lines.append({
            "request_item_id": str(item.id),
            "quantity": line.quantity,
            "substituted_component_id": str(line.substituted_component_id) if line.substituted_component_id else None,
            "serial_numbers": serial_numbers,
            "inventory_unit_ids": [str(unit.id) for unit in units],
        })

    _refresh_request_status(db, request)
    record_audit(
        db,
        membership=membership,
        action="inventory.components_issued",
        entity_type="component_request",
        entity_id=request.id,
        after={"issue_id": str(issue.id), "lines": audit_lines, "request_status": request.status},
    )
    db.commit()
    return ComponentIssueResponse(
        id=issue.id,
        request_id=request.id,
        status=issue.status,
        request_status=request.status,
        issue_line_ids=issue_line_ids,
        inventory_unit_ids=inventory_unit_ids,
    )


@router.post("/component-requests/{request_id}/reject", response_model=ComponentRequestResponse)
def reject_component_request(
    request_id: UUID,
    payload: RequestActionReason,
    membership: Membership = Depends(require_permissions("inventory.issue")),
    db: Session = Depends(current_db),
) -> ComponentRequestResponse:
    request = db.scalar(select(ComponentRequest).where(ComponentRequest.id == request_id, ComponentRequest.company_id == membership.company_id))
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component request not found")
    if request.status in {"fulfilled", "rejected", "partially_rejected", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Component request is not open")
    request.status = "partially_rejected" if db.scalar(
        select(ComponentRequestItem.id).where(ComponentRequestItem.request_id == request.id, ComponentRequestItem.issued_quantity > 0)
    ) else "rejected"
    request.rejection_reason = payload.reason
    record_audit(db, membership=membership, action="inventory.component_request_rejected", entity_type="component_request", entity_id=request.id, reason=payload.reason, after={"status": request.status})
    db.commit()
    return _component_request_response(db, request)


@router.post("/component-requests/{request_id}/cancel", response_model=ComponentRequestResponse)
def cancel_component_request(
    request_id: UUID,
    payload: RequestActionReason,
    membership: Membership = Depends(require_permissions("request.create")),
    db: Session = Depends(current_db),
) -> ComponentRequestResponse:
    request = db.scalar(select(ComponentRequest).where(ComponentRequest.id == request_id, ComponentRequest.company_id == membership.company_id))
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component request not found")
    if request.requested_by_membership_id != membership.id and not has_permission(membership, db, "completion.confirm"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the requester or an authorized manager can cancel this request")
    drone = db.get(Drone, request.drone_id)
    if not drone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drone not found")
    if drone.status != "confirmed":
        task_statuses = db.scalars(select(ProductionTask.status).where(ProductionTask.drone_id == drone.id)).all()
        if not task_statuses or any(task_status != "completed" for task_status in task_statuses):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Remaining quantity can be cancelled after production tasks are completed")
    if request.status in {"fulfilled", "rejected", "partially_rejected", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Component request is not pending")
    request.status = "cancelled"
    request.cancellation_reason = payload.reason
    record_audit(db, membership=membership, action="inventory.component_request_cancelled", entity_type="component_request", entity_id=request.id, reason=payload.reason, after={"status": request.status})
    db.commit()
    return _component_request_response(db, request)
