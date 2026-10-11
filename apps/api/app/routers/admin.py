from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..dependencies import current_db, require_permissions
from ..models import Membership, MembershipRole, RegisteredDevice, Role, User
from ..schemas import AdminUserSummary, UserCreate

router = APIRouter(prefix="/admin", tags=["administration"])


@router.post("/users", response_model=AdminUserSummary, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    membership: Membership = Depends(require_permissions("members.manage")),
    db: Session = Depends(current_db),
) -> AdminUserSummary:
    existing = db.scalar(select(User).where(User.email == str(payload.email)))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")
    user = User(
        auth_subject=payload.auth_subject,
        email=str(payload.email),
        display_name=payload.display_name,
        status="active" if payload.auth_subject else "invited",
    )
    db.add(user)
    db.flush()
    new_membership = Membership(company_id=membership.company_id, user_id=user.id, status="active")
    db.add(new_membership)
    db.flush()
    for code in payload.role_codes:
        role = db.scalar(select(Role).where(Role.company_id == membership.company_id, Role.code == code))
        if not role:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Unknown role: {code}")
        db.add(MembershipRole(membership_id=new_membership.id, role_id=role.id))
    record_audit(
        db,
        membership=membership,
        action="members.user_created",
        entity_type="user",
        entity_id=user.id,
        after={"email": user.email, "display_name": user.display_name, "role_codes": payload.role_codes},
    )
    db.commit()
    db.refresh(user)
    return AdminUserSummary(
        **user.__dict__,
        role_codes=payload.role_codes,
        membership_status=new_membership.status,
    )


@router.get("/users", response_model=list[AdminUserSummary])
def list_users(
    membership: Membership = Depends(require_permissions("members.read")),
    db: Session = Depends(current_db),
) -> list[AdminUserSummary]:
    rows = db.execute(
        select(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.company_id == membership.company_id)
        .order_by(User.display_name)
    ).all()
    role_rows = db.execute(
        select(MembershipRole.membership_id, Role.code)
        .join(Role, Role.id == MembershipRole.role_id)
        .where(Role.company_id == membership.company_id)
    ).all()
    role_codes_by_membership: dict[UUID, list[str]] = {}
    for membership_id, role_code in role_rows:
        role_codes_by_membership.setdefault(membership_id, []).append(role_code)
    return [
        AdminUserSummary(
            **user.__dict__,
            role_codes=sorted(role_codes_by_membership.get(company_membership.id, [])),
            membership_status=company_membership.status,
        )
        for user, company_membership in rows
    ]


@router.post("/users/{user_id}/device/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_user_device(
    user_id: UUID,
    membership: Membership = Depends(require_permissions("members.manage")),
    db: Session = Depends(current_db),
) -> None:
    target_membership = db.scalar(
        select(Membership).join(User, User.id == Membership.user_id).where(
            Membership.company_id == membership.company_id,
            Membership.user_id == user_id,
        )
    )
    if not target_membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    device = db.scalar(select(RegisteredDevice).where(RegisteredDevice.membership_id == target_membership.id))
    if device:
        device.revoked_at = datetime.now(UTC)
        record_audit(
            db,
            membership=membership,
            action="device.reset",
            entity_type="device",
            entity_id=device.id,
            before={"membership_id": str(target_membership.id)},
            reason="Administrator device reset",
        )
        db.commit()
