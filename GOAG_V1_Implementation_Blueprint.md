# GOAG V1 Implementation Blueprint

Status: Approved implementation baseline  
Scope: GOAG only  
Version: V1

## 1. Product boundary

V1 is a responsive web application for:

- User and role administration
- Attendance with GPS geofencing and one registered device per employee
- Drone creation, serial numbers, assignments, and production confirmation
- Serialized component inventory and traceability
- Component requests, partial issues, substitutions, returns, removals, replacements, and damage
- Suppliers and replenishment requests
- Customers, quotations, orders, sales, and delivery/sold-drone records
- Dashboards, search, audit history, and reversible corrections

Explicitly outside V1:

- Invoices, payments, pricing, discounts, and tax calculations
- After-sales/service operations
- Barcode or QR scanning
- Automatic paper-data import
- Full multi-company user interface

The database should still include `company_id` on core business tables so future company isolation does not require a redesign.

## 2. Approved technology stack

| Layer | Technology |
|---|---|
| Web application | Next.js, React, TypeScript, App Router |
| API | FastAPI, Pydantic, OpenAPI |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth with secure SSR cookies |
| Database access | SQLAlchemy and Alembic, or Supabase migrations consistently; do not mix migration ownership |
| Background jobs | Python worker with PostgreSQL job/outbox tables |
| Email | Transactional email provider called by the worker |
| Testing | Pytest, PostgreSQL integration tests, Playwright browser tests |
| Local development | Docker Compose |

The frontend must not write inventory or production data directly. All business mutations go through the FastAPI API.

## 3. Recommended repository structure

```text
goag-v1/
  apps/
    web/                 # Next.js frontend
    api/                 # FastAPI backend
    worker/              # email and background jobs
  packages/
    api-client/          # generated TypeScript client from OpenAPI
    shared-types/        # only genuinely shared types
  database/
    migrations/
    seeds/
  tests/
    api/
    integration/
    browser/
  infra/
    docker-compose.yml
  docs/
  .env.example
```

## 4. Cross-cutting rules

### Authentication and sessions

- Supabase Auth verifies identity.
- Next.js uses secure, HTTP-only cookie sessions.
- FastAPI verifies the Supabase identity and maps it to a GOAG membership.
- GOAG roles and permissions are stored in GOAG tables, not trusted from the browser.
- The Supabase service key is server-only and never sent to the browser.
- One registered device is allowed per employee; an authorized administrator can reset it.

### Authorization

Every API mutation checks:

1. Authenticated Supabase user
2. Active GOAG membership
3. Current role permissions
4. Ownership, assignment, or store/drone scope
5. Valid workflow state

Menu hiding is not authorization. Unauthorized API calls must return a clear 403 response.

### Audit and reversibility

The following actions create audit events:

- Role and user changes
- Attendance corrections and exceptions
- Stock receipts, issues, substitutions, returns, damage, removals, and replacements
- Drone creation, serial changes, assignments, reopening, and completion decisions
- Sales/order/delivery changes
- Managing Director corrections

Historical stock and production records are not silently overwritten. Corrections create a reasoned reversal or amendment linked to the original event.

### Status changes

Status fields are changed only through named business commands, not generic unrestricted PATCH requests.

### Idempotency and concurrency

- Every stock-changing command accepts an idempotency key.
- Repeated requests must not create duplicate stock movements.
- Related request lines, component units, and stock balances are locked in a stable order.
- Stock may never become negative.
- Repeated return receipt, issue, or completion requests must be safe.

## 5. Module map and dependencies

```text
Platform/Auth
    |
    +--> Administration/RBAC
    +--> Audit
    +--> Attendance
    +--> Production/Drones
              |
              +--> Inventory/Traceability
              +--> Requests and Issues
              +--> Returns/Removal/Replacement
    +--> Suppliers/Replenishment
    +--> Sales/Orders/Delivery
    +--> Dashboards/Reports
```

## 6. Module 1: Platform, authentication, and configuration

### Responsibilities

- Supabase Auth integration
- Session refresh and logout
- User-to-GOAG membership mapping
- Environment configuration
- Common API error format
- Request ID and correlation ID
- Application health checks

### Core data

- `auth.users` managed by Supabase
- `users`
- `companies`
- `memberships`
- `company_settings`
- `registered_devices`

### Required settings

- GOAG company identifier
- Company timezone
- Test worksite latitude/longitude
- Test geofence radius
- Global shift start/end times
- Attendance retention period
- Session and device policy

### Acceptance tests

- Unauthenticated users cannot access protected screens or APIs.
- Disabled memberships cannot perform actions.
- Session refresh works without exposing tokens to browser JavaScript.
- A second device is rejected until an authorized administrator resets the registered device.

## 7. Module 2: Administration and RBAC

### Official roles

| Role | V1 responsibility |
|---|---|
| Managing Director | Full access, users/roles, monitoring, sales, production, inventory, attendance |
| Production Manager | Drone creation, serial numbers, assignments, production confirmation, drone-side component actions |
| Store Manager | Inventory, stock-in/out, requests, suppliers, substitutions, store-side component actions |
| Sales Manager | Customers, quotations, orders, sales, delivery/sold-drone records |
| Technician | Assigned work, attendance, component requests, own issued components |
| After-Sales Manager | Reserved role only; no V1 features or permissions |

### Implementation

- Store permissions as database records.
- Assign multiple roles if needed, with effective permissions as the union.
- Protect final administrator removal.
- Record before/after role changes.
- Do not allow a role editor to grant permissions beyond its own authority.

### Acceptance tests

- Each role can perform only its approved actions.
- Technician cannot create drones or edit another technician's work.
- Store Manager cannot confirm a drone.
- Production Manager cannot approve store substitutions unless explicitly granted later.
- Managing Director can administer and correct records, with audit and reversal.

## 8. Module 3: Attendance and device registration

### Workflow

1. Employee presses Check in.
2. Browser requests GPS permission.
3. API validates registered device, coordinates, accuracy, time, worksite, and shift.
4. Attendance is accepted, rejected, or sent to a manager-approved exception flow.
5. Checkout is recorded when enabled.

### Core data

- `worksites`
- `attendance`
- `attendance_exceptions`
- `attendance_corrections`
- `registered_devices`
- `shift_settings`

### Rules

- V1 starts with one configurable GOAG worksite.
- Radius is configurable and initially tested around 100–200 metres.
- GPS denied or inaccurate means rejected attendance.
- Late attendance is calculated from global shift settings.
- Technicians cannot edit their own attendance.
- Manager-approved off-site attendance and corrections are audited.
- Location retention is configurable.

### Acceptance tests

- Login does not create attendance.
- Accepted check-in is inside the configured geofence.
- Off-site, denied, inaccurate, duplicate, and late cases behave correctly.
- Technician cannot change attendance after submission.
- Manager correction retains the original value and reason.

## 9. Module 4: Drone and production management

### Responsibilities

- Drone creation and serial number assignment
- Drone history
- Technician assignments
- Individual assignment completion
- Whole-drone completion report
- Production Manager confirmation
- Reopening a confirmed drone with a reason

### Core data

- `drones`
- `drone_assignments`
- `assignment_events`
- `completion_reports`
- `production_checklists`
- `drone_reopen_events`

### Rules

- Production Manager and Managing Director can create drones.
- Technicians cannot create drones or serial numbers.
- Multiple technicians may work on one drone.
- Individual task completion does not complete the drone.
- Completion confirmation checks required components, quantities, serials, tasks, unresolved issues, drone serial, and production checklist.
- Confirmed drones are locked except for authorized reopening.

### Acceptance tests

- Multiple technicians can be assigned and retain history.
- A technician completing an assignment does not complete the drone.
- A drone cannot be confirmed with missing required serials or unresolved component issues.
- Reopening requires an authorized manager and a reason.

## 10. Module 5: Component catalog and serialized inventory

### Responsibilities

- Component catalog
- All physical component units and serial numbers
- Stock receipts
- Available, held, installed, and damaged state
- Stock movement ledger
- Stock reconciliation

### Core data

- `components`
- `stock_locations`
- `component_units`
- `stock_receipts`
- `stock_receipt_lines`
- `stock_balances`
- `stock_movements`
- `damage_records`

### Rules

- Every physical unit is serialized.
- Serial entry is manual.
- Missing serials can remain pending after issue.
- A serial is required before installation and final drone confirmation.
- Known serials are unique within GOAG for the component type.
- Stock movement records are append-only.
- Available stock cannot become negative.
- A component unit cannot be actively installed in two drones.

### Acceptance tests

- Receipt creates one physical unit per serialized component.
- Issue without serial creates a pending unit without losing custody.
- Later serial entry updates the same unit and does not deduct stock again.
- Duplicate serials are rejected.
- Simultaneous issues cannot oversell the last available unit.

## 11. Module 6: Component requests, issues, and substitutions

### Request workflow

1. Technician selects an assigned drone.
2. Technician selects a component and quantity.
3. Technician enters a mandatory reason.
4. Store Manager approves and issues all or part of the request.
5. Remaining quantity stays pending/backordered.
6. Store Manager may reject or substitute a component.
7. Substitution records original component, replacement component, approver, reason, and transaction history.

### Core data

- `component_requests`
- `request_lines`
- `issues`
- `issue_lines`
- `issue_unit_allocations`
- `substitution_events`

### Rules

- Partial issue is supported.
- Insufficient stock leaves the remainder pending/backordered.
- Only Store Manager approves substitutions.
- Request cancellation after drone completion is allowed and audited.
- An issue cannot exceed available stock or the outstanding request quantity.

### Acceptance tests

- Request without a reason is rejected.
- Request for 10 with only 6 available issues 6 and leaves 4 pending.
- Rejection records a reason.
- Substitution preserves both requested and issued component history.
- Duplicate submit does not issue twice.
- Remaining quantity can be cancelled after drone completion with a reason.

## 12. Module 7: Installation, removal, replacement, returns, and damage

### Authority boundary

- Production Manager: drone-side installation, removal, and replacement decisions.
- Store Manager: physical store receipt, usable/damaged classification, stock movement, and custody.
- Every action records performer, approver, timestamp, reason, and related drone/component.

### Core data

- `installations`
- `component_removals`
- `component_replacements`
- `returns`
- `return_lines`
- `return_unit_allocations`
- `damage_records`

### Rules

- Installed components can be removed and returned to store.
- Removed components can be installed in another drone.
- Replacement closes the old installation and creates a new traceable installation.
- Damaged components remain separated from usable stock.
- Installed components cannot be returned as unused items.
- All transitions preserve the full component-to-drone history.

### Acceptance tests

```text
Component A -> Drone A -> Removed -> Store -> Drone B
```

- The complete chain remains visible.
- Store receipt cannot be recorded twice.
- Damaged return does not increase usable stock.
- A component cannot be installed while reserved for return.
- Removal and replacement require the correct authority.

## 13. Module 8: Suppliers and replenishment

### Responsibilities

- Supplier records
- Low-stock visibility
- Replenishment request preparation
- Email sending from the application
- Email status and retry handling

### Core data

- `suppliers`
- `replenishment_requests`
- `replenishment_lines`
- `outbox_jobs`

### Rules

- Replenishment requests do not increase stock.
- Stock increases only after Store Manager records a receipt.
- Email content is written by the user; there is no AI email feature.
- Send requires a review screen and explicit confirmation.
- Failed emails remain visible and retryable.

## 14. Module 9: Sales, quotations, orders, and delivery

### V1 scope

- Customers
- Quotations
- Orders
- Sale records
- Delivery records
- Sold-drone records linked to drone serial numbers

### Excluded from V1

- Invoice generation
- Prices and payment processing
- Discounts and tax
- Financial accounting

### Core data

- `customers`
- `quotations`
- `quotation_lines`
- `orders`
- `order_lines`
- `sales`
- `deliveries`
- `sold_drone_records`

### Acceptance tests

- Sales Manager can create and update customers, quotations, and orders.
- A delivery links to the correct drone serial number.
- A drone cannot be marked sold twice without an authorized correction.
- Managing Director can view and manage sales records.
- No invoice or payment screen appears in V1.

## 15. Module 10: Dashboards, search, and reporting

### Role dashboards

- Technician: attendance, assignments, requests, held components, pending serials, recent activity.
- Store Manager: stock levels, pending requests, backorders, substitutions, returns, damaged stock, suppliers.
- Production Manager: active drones, assignments, pending completion, unresolved component issues, checklists.
- Sales Manager: customers, quotations, orders, deliveries, sold drones.
- Managing Director: company-wide attendance, inventory, production, assignments, sales, and audit activity.

### Search

- Drone serial number
- Component serial number
- Request number
- Customer
- Order and delivery

All results must be filtered by the user’s permissions.

## 16. API conventions

Use REST JSON under `/api/v1`.

### Response format

```json
{
  "data": {},
  "meta": {"request_id": "..."}
}
```

### Error format

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Only 6 units are available.",
    "field_errors": [],
    "request_id": "..."
  }
}
```

Business writes should use idempotency keys. Lists should use cursor pagination. Generic PATCH must not directly change workflow status, stock balances, or audit history.

## 17. Build sequence

### Milestone 1: Foundation

- Repository and Docker Compose
- Supabase project configuration
- Authentication and secure cookies
- User/membership tables
- RBAC seed data
- API error and audit foundations

### Milestone 2: Inventory core

- Components and serialized units
- Receipts and stock movements
- Issues and partial issues
- Pending serial capture
- Concurrency and idempotency tests

### Milestone 3: Production

- Drones and serials
- Assignments
- Installation and traceability
- Returns, removals, replacements, and damage
- Completion checklist and confirmation

### Milestone 4: Attendance

- Worksite configuration
- Device registration
- Check-in, checkout, late status, exceptions, corrections

### Milestone 5: Suppliers and sales

- Suppliers and replenishment email
- Customers, quotations, orders, sales, and delivery

### Milestone 6: Dashboards and pilot readiness

- Role dashboards
- Search and reports
- Backup/restore test
- Security review
- GOAG acceptance testing

## 18. Definition of done for V1

V1 is ready for pilot use when:

- Each approved role has tested permissions.
- A full request-to-installation-to-confirmation flow works.
- Serialized component history is complete and searchable.
- Partial issues, substitutions, returns, removal, replacement, and damage are audited.
- Stock cannot become negative under concurrent actions.
- Attendance rules work with the test location configuration.
- Sales workflow works without invoice functionality.
- Managing Director corrections are reversible and audited.
- Backup restoration has been tested.
- GOAG stakeholders complete the acceptance scenarios and sign off.
