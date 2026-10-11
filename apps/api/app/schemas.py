from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=200)
    role_codes: list[str] = Field(min_length=1)
    auth_subject: str | None = None


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    status: str


class AdminUserSummary(UserSummary):
    role_codes: list[str] = Field(default_factory=list)
    membership_status: str


class MembershipSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    status: str


class MeResponse(BaseModel):
    user: UserSummary
    membership: MembershipSummary
    role_codes: list[str]
    permission_codes: list[str]


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=16, max_length=512)


class DeviceResponse(BaseModel):
    registered: bool
    last_seen_at: str


class AttendanceActionRequest(BaseModel):
    device_id: str = Field(min_length=16, max_length=512)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)
    gps_denied: bool = False


class AttendanceMemberResponse(BaseModel):
    membership_id: UUID
    display_name: str
    email: str


class AttendanceExceptionCreate(BaseModel):
    membership_id: UUID
    work_date: date
    reason: str = Field(min_length=1, max_length=1000)


class AttendanceExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    membership_id: UUID
    work_date: date
    reason: str
    status: str
    approved_by_membership_id: UUID
    approved_at: datetime


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    membership_id: UUID
    member_display_name: str | None = None
    member_email: str | None = None
    work_date: date
    status: str
    late: bool
    check_in_at: datetime
    check_out_at: datetime | None
    check_in_distance_m: float
    check_out_distance_m: float | None
    correction_reason: str | None


class AttendanceCorrectionRequest(BaseModel):
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    reason: str = Field(min_length=1, max_length=1000)


class DashboardAuditEventResponse(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    action_label: str
    subject: str | None = None
    status_label: str
    created_at: datetime


class DashboardSummaryResponse(BaseModel):
    inventory_in_stock: int | None = None
    inventory_issued: int | None = None
    pending_component_requests: int | None = None
    backordered_quantity: int | None = None
    drones_in_production: int | None = None
    confirmed_drones: int | None = None
    open_production_tasks: int | None = None
    my_attendance_days_last_30: int
    company_attendance_days_last_30: int | None = None
    my_attendance_today_status: str | None = None
    recent_audit_events: list[DashboardAuditEventResponse] = Field(default_factory=list)


class MailboxStatusResponse(BaseModel):
    configured: bool
    connected: bool
    provider: str
    mailbox_email: str | None
    message: str


class MailboxOAuthStartResponse(BaseModel):
    authorization_url: str


class MailboxSendRequest(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=250)
    body: str = Field(min_length=1, max_length=10000)


class MailboxSendResponse(BaseModel):
    message_id: str
    thread_id: str | None = None


class MailboxMessageSummary(BaseModel):
    id: str
    thread_id: str | None = None
    sender: str
    recipients: str
    subject: str
    snippet: str
    received_at: datetime | None = None
    label_ids: list[str] = Field(default_factory=list)
    unread: bool = False


class MailboxMessageListResponse(BaseModel):
    messages: list[MailboxMessageSummary]
    next_page_token: str | None = None


class MailboxThreadMessage(BaseModel):
    id: str
    thread_id: str | None = None
    sender: str
    recipients: str
    subject: str
    body: str
    sent_at: datetime | None = None
    label_ids: list[str] = Field(default_factory=list)


class MailboxThreadResponse(BaseModel):
    thread_id: str
    messages: list[MailboxThreadMessage]


class ComponentCatalogCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    serialized: bool = True
    description: str | None = None


class ComponentCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    category: str
    minimum_stock: int
    storage_location: str
    remarks: str
    serialized: bool
    description: str | None
    status: str


class InventoryUnitCreate(BaseModel):
    component_id: UUID
    serial_number: str | None = Field(default=None, min_length=1, max_length=150)
    condition: str = Field(default="good", min_length=1, max_length=32)
    location: str = Field(default="store", min_length=1, max_length=128)


class InventoryUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    component_id: UUID
    serial_number: str | None
    status: str
    location: str
    condition: str


class SerialAssignRequest(BaseModel):
    serial_number: str = Field(min_length=1, max_length=150)


class DroneCreate(BaseModel):
    drone_model_id: UUID | None = None
    serial_number: str | None = Field(default=None, min_length=1, max_length=150)
    notes: str | None = None


class DroneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drone_model_id: UUID | None
    serial_number: str | None
    status: str
    notes: str | None
    created_at: datetime


class DroneModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    status: str


class DroneModelCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


class ComponentRequestItemCreate(BaseModel):
    component_id: UUID
    requested_quantity: int = Field(gt=0)


class ComponentRequestCreate(BaseModel):
    drone_id: UUID
    items: list[ComponentRequestItemCreate] = Field(min_length=1)


class ComponentRequestItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    component_id: UUID
    component_code: str | None = None
    component_name: str | None = None
    requested_quantity: int
    issued_quantity: int
    pending_quantity: int
    status: str


class ComponentRequestResponse(BaseModel):
    id: UUID
    drone_id: UUID
    drone_serial_number: str | None = None
    status: str
    items: list[ComponentRequestItemResponse]
    created_at: datetime


class ComponentIssueLineCreate(BaseModel):
    request_item_id: UUID
    quantity: int = Field(gt=0)
    inventory_unit_ids: list[UUID] = Field(default_factory=list)
    serial_numbers: list[str] = Field(default_factory=list)
    substituted_component_id: UUID | None = None


class ComponentIssueCreate(BaseModel):
    lines: list[ComponentIssueLineCreate] = Field(min_length=1)
    notes: str | None = None


class ComponentIssueResponse(BaseModel):
    id: UUID
    request_id: UUID
    status: str
    request_status: str
    issue_line_ids: list[UUID]
    inventory_unit_ids: list[UUID]


class RequestActionReason(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ComponentActionCreate(BaseModel):
    action: str = Field(pattern="^(install|remove|return|damage|replace)$")
    inventory_unit_id: UUID
    issue_line_id: UUID | None = None
    replacement_for_id: UUID | None = None
    reason: str | None = Field(default=None, max_length=1000)


class ComponentInstallationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drone_id: UUID
    drone_serial_number: str | None = None
    inventory_unit_id: UUID
    component_code: str | None = None
    component_name: str | None = None
    component_serial_number: str | None = None
    action: str
    performed_by_membership_id: UUID
    approved_by_membership_id: UUID | None
    replacement_for_id: UUID | None
    reason: str | None
    occurred_at: datetime


class ProductionAssigneeResponse(BaseModel):
    membership_id: UUID
    user_id: UUID
    display_name: str
    email: str


class ProductionTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    assigned_to_membership_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ProductionTaskUpdate(BaseModel):
    status: str = Field(pattern="^(open|in_progress|completed|cancelled)$")
    notes: str | None = Field(default=None, max_length=2000)


class ProductionTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drone_id: UUID
    drone_serial_number: str | None = None
    title: str
    status: str
    assigned_to_membership_id: UUID | None
    assignee_display_name: str | None = None
    created_by_membership_id: UUID
    completed_by_membership_id: UUID | None
    notes: str | None
    completed_at: datetime | None
    created_at: datetime


class DroneConfirmationRequest(BaseModel):
    checklist: dict[str, bool]


class ReopenDroneRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class DroneConfirmationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    serial_number: str
    status: str
    confirmation_checklist: dict[str, bool]
    confirmed_at: datetime
