# GOAG Frontend Redesign Prompt

You are updating the frontend of the GOAG Operations application in this repository. Act as a senior product designer and senior frontend engineer. Redesign the authenticated experience at `/dashboard` into a calm, role-aware operations workspace for drone manufacturing and inventory teams.

## What I audited

The seeded development accounts are:

- Managing Director: `md@goag.example`
- Production Manager: `production.manager@goag.example`
- Store Manager: `store.manager@goag.example`
- Sales Manager: `sales.manager@goag.example`
- Technician: `technician@goag.example`
- After-Sales Manager: `after.sales@goag.example`

For local testing, all use password `123456`. This is development-only and must not be promoted to production.

The current page is a single very long document containing identity, module badges, summary cards, attendance, mailbox, opening inventory, catalog, drone creation, component requests, component issuing, serial assignment, traceability, tasks, confirmation, reopen, and request review. It is technically functional, but it reads like a test harness rather than an operations product.

Observed role behavior:

- Managing Director: broad company-wide access; needs an executive command center with audit and cross-domain visibility.
- Production Manager: needs active drones, assigned work, component issues, installation history, production checklist, and confirm/reopen actions.
- Store Manager: needs stock, opening inventory intake, request review, issue/substitute, pending serials, damaged/returned stock, and shared mailbox.
- Sales Manager: currently sees drone read metrics and attendance, but no usable sales workspace. The product brief calls for customers, quotations, orders, deliveries, and sold-drone records.
- Technician: needs own attendance, assigned tasks, held components/pending serials, component requests, and component actions. The current page still exposes too much catalog/history context before the useful actions.
- After-Sales Manager: currently has no V1 permissions. Show a deliberate empty state explaining that the after-sales workspace is not enabled yet; never show a red permission error.

Important current defects to fix as part of the redesign:

1. Store Manager and Sales Manager can see the `Inventory & production workflow` shell and a red `Missing permission` message even when only part of that workflow is allowed. Permission gating must happen before rendering a module or data request.
2. After-Sales Manager sees the same `Missing permission` error instead of a useful empty state.
3. Some role views show raw developer terms such as `Module 2`, `V1 modules`, permission counts, role codes, truncated UUIDs, and generic labels like `Component` or `Pending`.
4. The page has weak hierarchy, repeated cards, excessive vertical scrolling, and no task-oriented navigation.
5. The Sales Manager view has no sales module despite the product blueprint describing one.
6. Loading, error, and empty states are inconsistent and sometimes occupy the main workflow area as plain text.

## Design direction

Build a role-aware application shell:

- Persistent left navigation on desktop; compact drawer/bottom navigation on mobile.
- GOAG brand mark and workspace name at the top of the rail.
- Navigation items are generated from a central role/permission map, not scattered inline checks.
- Recommended primary items: Overview, Inventory, Production, Attendance, Sales, Mailbox, Team/Admin where permitted.
- Show only modules the current role can actually use. Do not show disabled-looking navigation items for inaccessible modules.
- Top bar: breadcrumb/page title, global search for drone serial, component serial, request, customer, or order, refresh, notifications/activity, and user menu.
- User menu should show human-readable display name and role name, not the raw role code.
- Use a centered content area with a max width around 1440px, 24px desktop spacing, and a clear two-column layout for dense operational pages.

Use the existing Next.js, TypeScript, Tailwind, and shadcn/ui stack. Preserve existing API contracts and RBAC behavior. Prefer composition over one giant component.

## Overview page behavior

The dashboard overview should be a concise control tower, not the place where every form is rendered.

Header:

- Greeting such as `Good morning, [name]`.
- Role-aware subtitle, for example `Here’s what needs your attention today.`
- Date range or `Today` context where useful.
- One primary quick action appropriate to the role.

KPI row:

- Render only metrics returned for the current permission set.
- Use 4–6 cards maximum, with a label, value, trend/context, and click-through target.
- Avoid displaying `null`, zero-value noise, or irrelevant metrics just to fill space.
- Suggested cards:
  - Managing Director: attendance exceptions, inventory in stock, drones in production, pending requests, open tasks, recent audit events.
  - Production Manager: active drones, my/open tasks, pending component issues, drafts awaiting completion, confirmed this period.
  - Store Manager: stock on hand, low-stock items, pending requests, backorders, returns/damaged items, unread mailbox.
  - Sales Manager: open quotations, orders in progress, upcoming deliveries, sold drones.
  - Technician: my open tasks, my component requests, components waiting for serials, today’s attendance.
  - After-Sales Manager: no operational KPIs in V1; use the reserved-role empty state.

Below the KPIs:

- `Needs attention` list with 3–5 actionable items. Each row has severity, readable entity name, short context, timestamp, and a clear action.
- `Recent activity` timeline/table with human-readable names and status badges.
- `Quick actions` as 2–4 prominent buttons, not buried at the bottom of the page.
- Keep deep forms and long tables in their respective modules.

## Role-specific module layouts

### Managing Director

Overview should emphasize company-wide visibility, attendance exceptions, operational risks, low stock, production bottlenecks, and audit activity. Provide drill-down links into Inventory, Production, Attendance, Sales, Team/Admin, and Mailbox. Do not make the director scroll through every operational form on the overview.

### Production Manager

Production page should use a tabbed or segmented layout:

- Active drones: cards/table showing serial, model, stage, completion %, assigned technician, blocked state.
- Tasks: filters for open, in progress, completed; quick assignment and status updates.
- Component issues: requests and unresolved serial/installation problems.
- Completion: checklist-driven confirmation and a separate, clearly destructive/reversible reopen flow.
- Traceability: installation history with readable drone serial, component, serial number, action, approval, and time.

Create drone and request components should open drawers or dialogs from clear primary actions instead of taking permanent page space.

### Store Manager

Store page should prioritize physical stock work:

- Stock health summary with low-stock and zero-stock emphasis.
- Opening inventory as an import/intake flow with a visible save state.
- Request review queue with status filters and row-level issue/reject actions.
- Issue components as a guided handover form showing requested quantity, available quantity, serial entry, and substitution approval.
- Separate queue for components missing serials.
- Returns/damaged stock as a simple action queue.
- Mailbox should be a separate Mailbox page or clearly secondary panel, not a full inbox and compose form directly below attendance.

### Sales Manager

Create a real Sales workspace consistent with the product blueprint: customers, quotations, orders, deliveries, and sold drones. If those API slices are not implemented yet, show a polished `Sales workspace coming next` state with the intended navigation and a short explanation; do not show production forms or a permission error.

### Technician

Technician landing page should be action-oriented:

- My tasks first, with status and drone serial.
- My component requests and request status.
- Components held or waiting for serial assignment.
- Component installation/action history relevant to the technician.
- Compact personal attendance card and history.

Keep the catalog as searchable reference content, preferably behind a tab or secondary panel.

### After-Sales Manager

Render a calm, intentional empty state:

- Title: `After-sales workspace is not enabled yet`
- Explain that this role is reserved for a future V1 module.
- Provide a `View my attendance` action if attendance is available and a `Contact administrator` or help action if one exists.
- Do not render the inventory/production module, red error banners, or inaccessible data requests.

## Visual system

Replace the current plain black-and-white document feel with a restrained operations UI:

- Warm neutral page background and white surfaces.
- One strong brand accent, preferably deep indigo/blue or a GOAG-approved color, used consistently for primary actions and active navigation.
- Semantic status colors: green success, amber attention, red destructive/blocking, blue informational. Always pair color with text/icon.
- Use a clear type scale: page title 28–32px, section title 18–22px, body 14–15px, metadata 12–13px.
- Use consistent 12–16px card padding, 12px radius, subtle borders/shadows, and fewer but stronger containers.
- Tables need sticky headers where useful, readable density, responsive horizontal scroll, empty rows, and status badges.
- Use skeletons for initial loading; use inline error blocks with retry; use empty states with an explanation and next action.
- Never expose raw UUIDs unless inside a secondary detail view. Prefer serial numbers, names, dates, and meaningful codes.
- Buttons must describe the action (`Review request`, `Issue components`, `Create drone`, `Open mailbox`) rather than generic labels.
- Destructive actions such as reject, cancel, mark damaged, reopen, or send must have appropriate confirmation and clear consequence text.

## Implementation constraints

- Keep server-side auth and existing Supabase session behavior intact.
- Keep API/RBAC enforcement authoritative on the backend; frontend gating is for clarity and UX only.
- Introduce reusable pieces such as `AppShell`, `RoleOverview`, `PermissionGate`, `MetricCard`, `NeedsAttentionList`, `ActivityList`, `ModuleHeader`, `EmptyState`, `LoadingSkeleton`, and `StatusBadge`.
- Centralize role labels, permission-to-navigation mapping, KPI selection, and empty-state copy.
- Do not fetch data for modules the current user cannot access.
- Remove or refactor the current `Missing permission` workflow behavior so inaccessible sections are omitted, not rendered as errors.
- Use URL state for module tabs and important filters when practical.
- Keep the existing functional forms and API calls working; move them into focused module views/drawers rather than deleting capabilities.
- Add accessible labels, visible focus states, keyboard support, and responsive behavior.

## Acceptance criteria

Test all six seeded accounts locally with password `123456`:

- No role sees a red permission error for a module that should simply be hidden.
- Every role lands on a useful overview with a clear primary action or intentional empty state.
- Managing Director sees company-wide oversight and audit context.
- Production Manager sees production-first work queues and completion controls.
- Store Manager sees inventory/request-first work queues and mailbox access.
- Sales Manager sees a sales workspace or a polished coming-soon state, never production workflow noise.
- Technician sees assigned work and requests before reference/catalog content.
- After-Sales Manager sees the reserved-role empty state and personal attendance only.
- Inaccessible modules do not trigger unnecessary API requests.
- No raw role codes, permission counts, truncated UUIDs, or developer-only labels appear in primary UI.
- Mobile layout is usable at 390px width; desktop layout is comfortable at 1440px width.
- Existing API tests and frontend production build still pass.

Before finishing, provide a short summary of the new information architecture, list any API gaps discovered for Sales, and verify each seeded role view.

## Second audit: findings in the current implementation

The first redesign pass is partially implemented. It is moving in the right direction, but do not treat the current UI as finished. The following issues were observed in the live app and source on 2026-10-09. Fix them in priority order and verify them with the seeded role matrix.

### P0 — fix before calling the redesign complete

#### 1. Do not allow the overview to hang forever in loading

Observed behavior: the live Managing Director overview remained on `Loading workspace` and `Refreshing…` for several seconds before the summary appeared. The client request in `role-overview.tsx` has no timeout, and the Next.js backend proxy in `app/api/backend/[...path]/route.ts` does not catch or time-limit a failed upstream `fetch`.

Why it matters: an operator cannot tell whether data is loading, the API is down, or the page is broken. A control tower must fail clearly and recoverably.

Required behavior:

- Add an `AbortController` timeout to client data requests, around 8–10 seconds unless the endpoint genuinely needs longer.
- Add timeout/error handling in the Next.js proxy and return a useful 502/504 JSON response instead of leaving the request pending.
- Replace the endless spinner with an `ErrorState` containing: `Operational data is unavailable`, a short explanation, `Retry`, and a secondary `Open attendance` or `Return to overview` action where appropriate.
- Keep the last successful data visible during a refresh; do not blank the page while refreshing.
- Test with the API stopped and with a slow response.

#### 2. Remove or implement dead top-bar controls

Observed behavior: `Refresh current workspace` is rendered by `AppShell` but has no click handler. `Global search` is rendered as an input but has no state, submit behavior, results, or route integration.

Why it matters: dead controls reduce trust and make the workspace feel like a mockup.

Required behavior:

- Wire refresh to the active page using `router.refresh()` plus a page/module refresh callback, or remove the control until it works.
- Implement global search as a real accessible combobox or route-backed search surface. Start with existing drone serial, component serial, request, and order/searchable entities; do not present a search box that silently does nothing.
- If search must wait for a backend endpoint, show a clearly disabled or `Coming soon` state with explanatory text instead of a fake active input.

#### 3. Fix inaccurate role metrics

Observed behavior: the Technician overview labels `inventory_issued` as `Held components`, but the existing dashboard summary counts all company units marked `issued` or `installed`; it is not technician-specific. The Managing Director overview presents `Attendance days` from `my_attendance_days_last_30` while the subtitle promises company-wide visibility.

Why it matters: operational metrics must be trustworthy. A wrong label can cause a user to make a wrong decision.

Required behavior:

- Either add correctly scoped API fields such as `my_held_components` and `company_attendance_days`, or change the labels to describe the actual scope.
- Never label company-wide data as `My …`, and never label personal data as company-wide.
- Document the scope under each KPI when the audience could misread it.
- Do not add a KPI just to fill an empty grid cell.

#### 4. Remove raw IDs from primary UI surfaces

Observed behavior: Store Manager request-review rows show truncated drone IDs such as `be3d6092` because the UI does not have a readable drone serial in that data path. Team administration also renders `user.id.slice(0, 8)` below every user name. Production has fallbacks such as `Component`, `Pending`, and truncated UUIDs.

Why it matters: operators work with serial numbers, names, and request numbers—not database identifiers.

Required behavior:

- Extend the protected response models/endpoints to include the related drone serial, component code/name, request number, and display names needed by each role.
- Do not solve this by displaying longer UUIDs or by exposing IDs in a smaller font.
- Use `—` with an explanatory tooltip only when a human-readable value genuinely does not exist.
- Keep UUIDs only in secondary support/audit detail views.

### P1 — fix in the current frontend pass

#### 5. Remove duplicate page hierarchy

Observed behavior: `/dashboard/production` and `/dashboard/inventory` each show a route header (`Production` / `Inventory`) followed immediately by another inner module header with the same title, subtitle, and refresh action.

Why it matters: the user sees two page introductions before reaching the work. The shell should establish location once, and the module should establish the work context once.

Required behavior:

- Keep one route-level `ModuleHeader` with title, concise purpose, refresh, and primary action.
- Remove the duplicate inner title block from `WorkflowPanel`, `InventoryModule`, and `ProductionModule`, or make the inner block a distinct tab/section title.
- Replace the developer-facing `Role-filtered workspace` badge with a useful operational context or remove it.

#### 6. Make the overview header responsive and less repetitive

Observed behavior: at the current narrow viewport the greeting wraps into multiple lines and `Today's operational view` becomes a narrow two-line block on the right. The role label is repeated in the page header and again inside the overview card.

Required behavior:

- At widths below roughly 768px, stack the header into one column and let the greeting use the available width.
- Keep the date/context as a small metadata line below the subtitle, not a separate narrow column.
- Show the role label once; the overview card should say `Today's overview`, not repeat `Managing Director` or `Technician`.
- Check the exact layout at 390px and 1440px.

#### 7. Replace generic activity copy with useful activity

Observed behavior: the overview activity panel frequently renders every event as `Operational activity` with a generic `Recorded` badge. The existing action map only covers a small subset of actual audit actions.

Why it matters: a recent-activity panel that does not identify what happened is visual noise, especially for the Managing Director.

Required behavior:

- Map all current audit actions to human-readable labels, including component request, component issue, installation, task, confirmation, reopen, attendance, and mailbox actions.
- Show the relevant human-readable subject: drone serial, component code, request number, user name, or mailbox subject.
- Use a meaningful status badge such as `Completed`, `Approved`, `Sent`, or `Updated`; do not use `Recorded` for everything.
- If the current audit API only returns codes and IDs, add display fields or a permission-safe activity projection rather than guessing in the browser.

#### 8. Make Store Manager inventory action-first

Observed behavior: the Store Manager must pass through Opening inventory and a 26-row component catalog before reaching `Issue components`, `Assign component serials`, and `Request review`. The primary work queues are below reference content.

Required behavior:

- Put stock-health KPIs, request review, pending handover, missing serials, and damaged/returned queues first.
- Move the full catalog into a secondary `Catalog` tab or collapsible reference section.
- Keep opening inventory in a focused intake view; show a blank-state prompt before inserting a large empty row by default.
- Add minimum-stock/low-stock status using the seeded `minimum_stock` value. A quantity column alone is not enough for a store operator.
- Preserve the existing forms and APIs; change the order and grouping, not the business rules.

#### 9. Prevent test fixtures from looking like production data

Observed behavior: the live Store Manager catalog contains entries such as `PW-E2E-…` and `Playwright component …`, and the production tables contain Playwright-generated drones/tasks/components.

Why it matters: seeded test records undermine visual QA and make the application look unreliable to a real operator.

Required behavior:

- Keep automated test data isolated from the development/demo company, or reset the demo dataset before a visual review.
- Do not silently hide business records in the frontend by filtering names that contain `PW-E2E`.
- Add a documented development-data reset/fixture strategy so screenshots and acceptance tests use intentional records.

#### 10. Keep production useful without reverting to a long form page

Observed behavior: Production now uses dialogs for create/request/traceability, which is good, but the page still places full installation history, production tasks, and completion controls in one long flow with no tabs, filters, or summary context.

Required behavior:

- Add production summary cards or a compact status strip near the top.
- Add clear tabs or filters for `Active drones`, `Tasks`, `Component issues`, `Traceability`, and `Completion`.
- Give tables empty states and status filters; do not make users scan every historical row to find open work.
- Keep dialogs for creation and destructive/reversible actions, with clear consequences and focus management.

#### 11. Style the authentication and entry pages consistently

Observed behavior: `apps/web/app/login/page.tsx` still uses mostly raw HTML and inline styles, unlike the redesigned authenticated shell. The home page is also a technical status page with plain links.

Required behavior:

- Give login a proper GOAG brand layout, responsive card, clear field states, password visibility affordance if appropriate, loading state, and inline error state.
- Use the same color tokens, typography, focus rings, and spacing as the workspace.
- Either redesign `/` as a lightweight branded entry page or redirect authenticated users directly to the workspace and keep unauthenticated users on a clear sign-in CTA.

#### 12. Add confirmation and feedback to admin actions

Observed behavior: Team administration exposes `Reset device` as a direct row action. It is a consequential action but does not have the same confirmation/feedback treatment as workflow actions.

Required behavior:

- Confirm before resetting a device and explain that the member will need to register again.
- Show success/error feedback tied to the affected member.
- Preserve the audit trail and do not add a destructive action without a clear recovery path.

## Second-audit acceptance checklist

Before declaring this pass complete, verify:

- Stopping or delaying the API produces a retryable error state, never an infinite spinner.
- The top-bar refresh button changes the active workspace or is not rendered.
- Global search either returns results or is explicitly marked unavailable; it is never a dead input.
- Every KPI's scope is accurate for its role.
- No primary table shows UUID fragments, generic `Component`, generic `Operational activity`, or unexplained `Pending` values when a readable value can be supplied.
- Inventory puts action queues before the catalog.
- Test fixture records are isolated from visual-review data.
- Production has filters/tabs or equivalent prioritization instead of one undifferentiated long page.
- Login and home match the authenticated visual system.
- All six seeded roles still pass the route-access matrix and no inaccessible endpoint is fetched.
