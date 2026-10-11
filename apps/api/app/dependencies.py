from collections.abc import Callable, Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .audit import record_audit
from .auth import Identity, get_identity
from .db import get_db
from .models import Membership, MembershipRole, Permission, Role, RolePermission, User


def current_db() -> Generator[Session, None, None]:
    yield from get_db()


def current_membership(
    identity: Identity = Depends(get_identity), db: Session = Depends(current_db)
) -> Membership:
    user = db.scalar(select(User).where(User.auth_subject == identity.subject))
    if not user and identity.email:
        invited_user = db.scalar(
            select(User).where(
                func.lower(User.email) == identity.email.lower(),
                User.status == "invited",
            )
        )
        if invited_user:
            invited_membership = db.scalar(
                select(Membership).where(
                    Membership.user_id == invited_user.id,
                    Membership.status == "active",
                )
            )
            if invited_membership:
                invited_user.auth_subject = identity.subject
                invited_user.status = "active"
                record_audit(
                    db,
                    membership=invited_membership,
                    action="members.auth_linked",
                    entity_type="user",
                    entity_id=invited_user.id,
                    after={"email": invited_user.email},
                    reason="Linked invited user during first authenticated request",
                )
                db.commit()
                user = invited_user
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GOAG membership is not active")
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.status == "active"))
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="GOAG membership is not active")
    return membership


def granted_permissions(membership: Membership, db: Session) -> set[str]:
    rows = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_code == Permission.code)
        .join(Role, Role.id == RolePermission.role_id)
        .join(MembershipRole, MembershipRole.role_id == Role.id)
        .where(MembershipRole.membership_id == membership.id)
    ).all()
    return {row[0] for row in rows}


def has_permission(membership: Membership, db: Session, permission: str) -> bool:
    return permission in granted_permissions(membership, db)


def require_permissions(*required: str) -> Callable:
    def dependency(
        membership: Membership = Depends(current_membership), db: Session = Depends(current_db)
    ) -> Membership:
        granted = granted_permissions(membership, db)
        missing = set(required) - granted
        if missing:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission")
        return membership

    return dependency
