from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..dependencies import current_db, current_membership
from ..device import hash_device_id
from ..models import (
    Membership,
    MembershipRole,
    Permission,
    RegisteredDevice,
    Role,
    RolePermission,
    User,
)
from ..schemas import (
    DeviceRegisterRequest,
    DeviceResponse,
    MembershipSummary,
    MeResponse,
    UserSummary,
)

router = APIRouter(prefix="/me", tags=["identity"])


@router.get("", response_model=MeResponse)
def get_me(membership: Membership = Depends(current_membership), db: Session = Depends(current_db)) -> MeResponse:
    user = db.get(User, membership.user_id)
    role_rows = db.execute(
        select(Role.code)
        .join(MembershipRole, MembershipRole.role_id == Role.id)
        .where(MembershipRole.membership_id == membership.id)
    ).all()
    permission_rows = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_code == Permission.code)
        .join(Role, Role.id == RolePermission.role_id)
        .join(MembershipRole, MembershipRole.role_id == Role.id)
        .where(MembershipRole.membership_id == membership.id)
    ).all()
    return MeResponse(
        user=UserSummary.model_validate(user),
        membership=MembershipSummary.model_validate(membership),
        role_codes=sorted({row[0] for row in role_rows}),
        permission_codes=sorted({row[0] for row in permission_rows}),
    )


@router.post("/device", response_model=DeviceResponse)
def register_device(
    payload: DeviceRegisterRequest,
    membership: Membership = Depends(current_membership),
    db: Session = Depends(current_db),
) -> DeviceResponse:
    device_hash = hash_device_id(payload.device_id)
    existing = db.scalar(select(RegisteredDevice).where(RegisteredDevice.membership_id == membership.id))
    now = datetime.now(UTC)
    if existing and existing.revoked_at is None and not hmac_compare(existing.device_id_hash, device_hash):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A different device is already registered")
    if existing and existing.revoked_at is not None:
        existing = RegisteredDevice(membership_id=membership.id, device_id_hash=device_hash, last_seen_at=now)
        db.add(existing)
        db.flush()
    elif existing:
        existing.device_id_hash = device_hash
        existing.last_seen_at = now
    else:
        existing = RegisteredDevice(membership_id=membership.id, device_id_hash=device_hash, last_seen_at=now)
        db.add(existing)
        db.flush()
    record_audit(
        db,
        membership=membership,
        action="device.registered",
        entity_type="device",
        entity_id=existing.id,
        after={"membership_id": str(membership.id)},
    )
    db.commit()
    return DeviceResponse(registered=True, last_seen_at=now.isoformat())


def hmac_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left, right)
