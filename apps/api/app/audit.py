from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .models import AuditEvent, Membership


def record_audit(
    db: Session,
    *,
    membership: Membership,
    action: str,
    entity_type: str,
    entity_id: UUID | str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        company_id=membership.company_id,
        actor_membership_id=membership.id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_data=before,
        after_data=after,
        reason=reason,
        correlation_id=correlation_id,
    )
    db.add(event)
    return event

