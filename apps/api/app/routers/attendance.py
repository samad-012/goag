import hmac
from datetime import UTC, date, datetime, time, timedelta
from math import asin, cos, radians, sin, sqrt
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import get_settings
from ..dependencies import current_db, current_membership, require_permissions
from ..device import hash_device_id
from ..models import (
    AttendanceException,
    AttendanceRecord,
    Company,
    Membership,
    RegisteredDevice,
    User,
)
from ..schemas import (
    AttendanceActionRequest,
    AttendanceCorrectionRequest,
    AttendanceExceptionCreate,
    AttendanceExceptionResponse,
    AttendanceMemberResponse,
    AttendanceResponse,
)

router = APIRouter(prefix="/attendance", tags=["attendance"])


def distance_in_metres(latitude: float, longitude: float, target_latitude: float, target_longitude: float) -> float:
    earth_radius_m = 6_371_000
    latitude_delta = radians(target_latitude - latitude)
    longitude_delta = radians(target_longitude - longitude)
    a = sin(latitude_delta / 2) ** 2 + cos(radians(latitude)) * cos(radians(target_latitude)) * sin(
        longitude_delta / 2
    ) ** 2
    return 2 * earth_radius_m * asin(sqrt(a))


def _registered_device(membership: Membership, device_id: str, db: Session) -> RegisteredDevice:
    device = db.scalar(
        select(RegisteredDevice).where(
            RegisteredDevice.membership_id == membership.id,
            RegisteredDevice.revoked_at.is_(None),
        )
    )
    if not device or not hmac.compare_digest(device.device_id_hash, hash_device_id(device_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Register this device before recording attendance",
        )
    return device


def _validated_location(
    payload: AttendanceActionRequest, membership: Membership, work_date: date, db: Session
) -> tuple[float, float, float]:
    settings = get_settings()
    if payload.gps_denied or payload.latitude is None or payload.longitude is None or payload.accuracy_m is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GPS location is required")
    if payload.accuracy_m > settings.goag_max_gps_accuracy_m:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="GPS accuracy is too poor")
    distance = distance_in_metres(
        payload.latitude,
        payload.longitude,
        settings.goag_test_worksite_lat,
        settings.goag_test_worksite_lon,
    )
    if distance > settings.goag_test_geofence_radius_m and not db.scalar(
        select(AttendanceException).where(
            AttendanceException.company_id == membership.company_id,
            AttendanceException.membership_id == membership.id,
            AttendanceException.work_date == work_date,
            AttendanceException.status == "approved",
        )
    ):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Outside approved GOAG geofence")
    return payload.latitude, payload.longitude, distance


def _company_clock(membership: Membership, db: Session) -> tuple[Company, ZoneInfo, datetime]:
    company = db.get(Company, membership.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GOAG company not found")
    try:
        timezone = ZoneInfo(company.timezone)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid company timezone") from exc
    local_now = datetime.now(UTC).astimezone(timezone)
    return company, timezone, local_now


def _today_record(membership: Membership, work_date: date, db: Session) -> AttendanceRecord | None:
    return db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.membership_id == membership.id,
            AttendanceRecord.work_date == work_date,
        )
    )


def _attendance_response(record: AttendanceRecord, db: Session) -> AttendanceResponse:
    member = db.execute(
        select(User.display_name, User.email)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.id == record.membership_id)
    ).first()
    return AttendanceResponse(
        **{
            **AttendanceResponse.model_validate(record).model_dump(),
            "member_display_name": member[0] if member else None,
            "member_email": member[1] if member else None,
        }
    )


@router.post("/check-in", response_model=AttendanceResponse)
def check_in(
    payload: AttendanceActionRequest,
    membership: Membership = Depends(require_permissions("attendance.check_in")),
    db: Session = Depends(current_db),
) -> AttendanceResponse:
    _, timezone, local_now = _company_clock(membership, db)
    work_date = local_now.date()
    device = _registered_device(membership, payload.device_id, db)
    latitude, longitude, distance = _validated_location(payload, membership, work_date, db)
    if _today_record(membership, work_date, db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendance is already checked in today")

    settings = get_settings()
    try:
        shift_start = time.fromisoformat(settings.goag_shift_start)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid shift start time") from exc
    shift_start_at = datetime.combine(work_date, shift_start, tzinfo=timezone)
    late = local_now > shift_start_at + timedelta(minutes=settings.goag_late_grace_minutes)
    attendance = AttendanceRecord(
        company_id=membership.company_id,
        membership_id=membership.id,
        work_date=work_date,
        status="late" if late else "present",
        late=late,
        check_in_at=local_now,
        check_in_latitude=latitude,
        check_in_longitude=longitude,
        check_in_accuracy_m=payload.accuracy_m,
        check_in_distance_m=distance,
        device_id_hash=device.device_id_hash,
    )
    db.add(attendance)
    device.last_seen_at = datetime.now(UTC)
    db.flush()
    record_audit(
        db,
        membership=membership,
        action="attendance.checked_in",
        entity_type="attendance",
        entity_id=attendance.id,
        after={"work_date": work_date.isoformat(), "late": late, "distance_m": round(distance, 2)},
    )
    db.commit()
    db.refresh(attendance)
    return _attendance_response(attendance, db)


@router.post("/check-out", response_model=AttendanceResponse)
def check_out(
    payload: AttendanceActionRequest,
    membership: Membership = Depends(require_permissions("attendance.check_in")),
    db: Session = Depends(current_db),
) -> AttendanceResponse:
    _, _, local_now = _company_clock(membership, db)
    device = _registered_device(membership, payload.device_id, db)
    latitude, longitude, distance = _validated_location(payload, membership, local_now.date(), db)
    attendance = _today_record(membership, local_now.date(), db)
    if not attendance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check in before checking out")
    if attendance.check_out_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attendance is already checked out today")
    attendance.check_out_at = local_now
    attendance.check_out_latitude = latitude
    attendance.check_out_longitude = longitude
    attendance.check_out_accuracy_m = payload.accuracy_m
    attendance.check_out_distance_m = distance
    device.last_seen_at = datetime.now(UTC)
    record_audit(
        db,
        membership=membership,
        action="attendance.checked_out",
        entity_type="attendance",
        entity_id=attendance.id,
        after={"work_date": attendance.work_date.isoformat(), "distance_m": round(distance, 2)},
    )
    db.commit()
    db.refresh(attendance)
    return _attendance_response(attendance, db)


@router.get("/me", response_model=list[AttendanceResponse])
def my_attendance(
    membership: Membership = Depends(current_membership),
    db: Session = Depends(current_db),
) -> list[AttendanceResponse]:
    today = datetime.now(UTC).date()
    rows = db.scalars(
        select(AttendanceRecord)
        .where(AttendanceRecord.membership_id == membership.id, AttendanceRecord.work_date >= today - timedelta(days=30))
        .order_by(AttendanceRecord.work_date.desc())
    ).all()
    return [_attendance_response(row, db) for row in rows]


@router.get("/members", response_model=list[AttendanceMemberResponse])
def attendance_members(
    membership: Membership = Depends(require_permissions("attendance.read_all")),
    db: Session = Depends(current_db),
) -> list[AttendanceMemberResponse]:
    rows = db.execute(
        select(Membership.id, User.display_name, User.email)
        .join(User, User.id == Membership.user_id)
        .where(Membership.company_id == membership.company_id, Membership.status == "active")
        .order_by(User.display_name)
    ).all()
    return [AttendanceMemberResponse(membership_id=row[0], display_name=row[1], email=row[2]) for row in rows]


@router.get("/exceptions", response_model=list[AttendanceExceptionResponse])
def list_exceptions(
    work_date: date | None = None,
    membership: Membership = Depends(require_permissions("attendance.read_all")),
    db: Session = Depends(current_db),
) -> list[AttendanceExceptionResponse]:
    query = select(AttendanceException).where(AttendanceException.company_id == membership.company_id)
    if work_date:
        query = query.where(AttendanceException.work_date == work_date)
    rows = db.scalars(query.order_by(AttendanceException.work_date.desc())).all()
    return [AttendanceExceptionResponse.model_validate(row) for row in rows]


@router.post("/exceptions", response_model=AttendanceExceptionResponse, status_code=status.HTTP_201_CREATED)
def approve_exception(
    payload: AttendanceExceptionCreate,
    membership: Membership = Depends(require_permissions("attendance.correct")),
    db: Session = Depends(current_db),
) -> AttendanceExceptionResponse:
    target = db.scalar(
        select(Membership).where(
            Membership.id == payload.membership_id,
            Membership.company_id == membership.company_id,
            Membership.status == "active",
        )
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance member not found")
    if db.scalar(
        select(AttendanceException).where(
            AttendanceException.membership_id == payload.membership_id,
            AttendanceException.work_date == payload.work_date,
        )
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An exception already exists for this employee and date")
    exception = AttendanceException(
        company_id=membership.company_id,
        membership_id=payload.membership_id,
        work_date=payload.work_date,
        reason=payload.reason,
        approved_by_membership_id=membership.id,
    )
    db.add(exception)
    db.flush()
    record_audit(
        db,
        membership=membership,
        action="attendance.exception_approved",
        entity_type="attendance_exception",
        entity_id=exception.id,
        after={"membership_id": str(payload.membership_id), "work_date": payload.work_date.isoformat()},
        reason=payload.reason,
    )
    db.commit()
    db.refresh(exception)
    return AttendanceExceptionResponse.model_validate(exception)


@router.get("", response_model=list[AttendanceResponse])
def all_attendance(
    work_date: date | None = None,
    membership: Membership = Depends(require_permissions("attendance.read_all")),
    db: Session = Depends(current_db),
) -> list[AttendanceResponse]:
    query = select(AttendanceRecord).where(AttendanceRecord.company_id == membership.company_id)
    if work_date:
        query = query.where(AttendanceRecord.work_date == work_date)
    rows = db.scalars(query.order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.check_in_at.desc())).all()
    return [_attendance_response(row, db) for row in rows]


@router.post("/{attendance_id}/correct", response_model=AttendanceResponse)
def correct_attendance(
    attendance_id: UUID,
    payload: AttendanceCorrectionRequest,
    membership: Membership = Depends(require_permissions("attendance.correct")),
    db: Session = Depends(current_db),
) -> AttendanceResponse:
    attendance = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.id == attendance_id,
            AttendanceRecord.company_id == membership.company_id,
        )
    )
    if not attendance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance record not found")
    before = {
        "check_in_at": attendance.check_in_at.isoformat(),
        "check_out_at": attendance.check_out_at.isoformat() if attendance.check_out_at else None,
    }
    if payload.check_in_at:
        attendance.check_in_at = payload.check_in_at
    if payload.check_out_at:
        attendance.check_out_at = payload.check_out_at
    if attendance.check_out_at and attendance.check_out_at < attendance.check_in_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Checkout must be after check-in")
    attendance.corrected_by_membership_id = membership.id
    attendance.correction_reason = payload.reason
    record_audit(
        db,
        membership=membership,
        action="attendance.corrected",
        entity_type="attendance",
        entity_id=attendance.id,
        before=before,
        after={
            "check_in_at": attendance.check_in_at.isoformat(),
            "check_out_at": attendance.check_out_at.isoformat() if attendance.check_out_at else None,
        },
        reason=payload.reason,
    )
    db.commit()
    db.refresh(attendance)
    return _attendance_response(attendance, db)
