# GOAG Frontend Redesign Implementation Plan

> **Current execution starts here:** begin with Section 13 (plan-review corrections) and Section 9 (remaining implementation order). Sections 1–7 describe the original design context and completed phases; do not rebuild work already listed as implemented in Section 8.

## 1. Objective

Redesign the authenticated Next.js experience from one long workflow document into a calm, role-aware operations workspace while preserving the existing Supabase session flow, FastAPI contracts, RBAC enforcement, serialized inventory workflow, attendance, and shared-mailbox functionality.

The redesign will improve information architecture and access clarity first. It will not weaken backend authorization or remove working capabilities; existing forms will move into focused module pages, tabs, drawers, or dialogs.

## 2. Current baseline

The current dashboard is assembled in `apps/web/app/dashboard/page.tsx` and renders these large components in sequence:

- `operational-dashboard.tsx`
- `attendance-panel.tsx`
- `email-panel.tsx`
- `workflow-panel.tsx`

The current API has identity, attendance, dashboard-summary, email, inventory, production, and admin routers. It does not yet expose customers, quotations, orders, deliveries, or sold-drone records.

The redesign therefore has two tracks:

1. Frontend shell, navigation, role-specific overviews, workflow separation, responsive states, and permission gating.
2. A polished Sales placeholder until the Sales API is implemented.

## 3. Target information architecture

### Application shell

Create a persistent `AppShell` with:

- Desktop left rail and mobile drawer/bottom navigation.
- GOAG mark, workspace name, and active navigation state.
- Top bar with breadcrumb, page title, global search, refresh/activity controls, and user menu.
- Human-readable display name and role label in the user menu.
- Central content area with a maximum width near 1440px and responsive spacing.

### Routes

Use route-level module boundaries so the overview does not render every form:

- `/dashboard` — role-aware overview/control tower.
- `/dashboard/inventory` — stock, opening inventory, request review, issues, serials, returns/damaged queue.
- `/dashboard/production` — active drones, tasks, component issues, traceability, confirmation/reopen.
- `/dashboard/attendance` — own attendance and manager controls where permitted.
- `/dashboard/sales` — Sales workspace or coming-soon state until APIs exist.
- `/dashboard/mailbox` — shared mailbox for Managing Director and Store Manager only.
- `/dashboard/team` — Managing Director user administration.

The first implementation may keep the existing page as a client-side shell with URL query tabs if introducing multiple route files would slow delivery, but the final structure should use route-level boundaries for module data isolation.

## 4. Central access and display configuration

Add a single configuration module, for example `apps/web/lib/workspace-config.ts`, containing:

- Human-readable role labels.
- Permission-to-navigation rules.
- Module labels, descriptions, icons, and route targets.
- Role-specific overview KPI definitions.
- Empty-state copy, including the reserved After-Sales state.
- Human-readable status and action labels.

Add reusable access primitives:

- `PermissionGate` — renders children only when the permission is present.
- `RoleGate` — handles role-specific variations without scattered role-code checks.
- `useWorkspaceAccess` or an equivalent derived access object.
- `getVisibleNavigation()` — filters navigation before rendering and before module data requests.

Frontend gates are for UX only. FastAPI remains authoritative.

## 5. Delivery phases

> Planning note: Sections 1–7 describe the original target and delivery history. Do not restart those phases or recreate components that are already present. The executable backlog begins in Section 8 (`Implementation status after the second audit`) and is refined by Sections 9, 12, and 13 below. When an older section conflicts with a later audit finding, the later finding wins.

### Phase 0 — Baseline and safety

1. Capture current behavior for all six seeded accounts at desktop and mobile widths.
2. Record current API calls made by each role.
3. Add a lightweight frontend test setup if absent.
4. Preserve the current dashboard behind a temporary feature flag or git checkpoint during migration.

Deliverable: a repeatable baseline and no regression risk while replacing the page.

### Phase 1 — Shell and visual foundation

Create:

- `apps/web/components/app-shell.tsx`
- `apps/web/components/app-sidebar.tsx`
- `apps/web/components/top-bar.tsx`
- `apps/web/components/user-menu.tsx`
- `apps/web/components/global-search.tsx`
- `apps/web/components/module-header.tsx`
- `apps/web/components/status-badge.tsx`
- `apps/web/components/empty-state.tsx`
- `apps/web/components/loading-skeleton.tsx`
- `apps/web/components/error-state.tsx`

Update:

- `apps/web/app/globals.css` for warm neutral background, indigo/blue accent, semantic colors, focus rings, and responsive layout tokens.
- Existing shadcn components where needed for navigation, dropdowns, dialogs, tabs, skeletons, and badges.

Acceptance checks:

- Keyboard navigation and visible focus states.
- Mobile layout usable at 390px.
- Desktop layout comfortable at 1440px.
- No raw role codes or permission counts in the primary shell.

### Phase 2 — Access map and overview control tower

Refactor `apps/web/app/dashboard/page.tsx` so it only loads:

- Current-user identity.
- Central access configuration.
- `AppShell`.
- `RoleOverview`.

Create:

- `apps/web/components/role-overview.tsx`
- `apps/web/components/metric-card.tsx`
- `apps/web/components/needs-attention-list.tsx`
- `apps/web/components/activity-list.tsx`
- `apps/web/components/quick-actions.tsx`

Overview behavior:

- Greeting and role-aware subtitle.
- Four to six meaningful KPIs maximum.
- Needs-attention queue with readable names and actionable links.
- Recent activity with human-readable status badges.
- Two to four role-specific quick actions.
- No deep forms or long tables.

Extend the dashboard summary API only where the current response cannot support the intended role view. Avoid showing irrelevant zero or null cards.

### Phase 3 — Module separation and permission-safe data loading

Split the existing workflow and panels into focused module components:

- `inventory-module.tsx`
- `production-module.tsx`
- `attendance-module.tsx`
- `mailbox-module.tsx`
- `team-module.tsx`

Move forms into dialogs/drawers:

- Create drone.
- Request components.
- Issue/substitute components.
- Add serials.
- Record installation actions.
- Add/assign production tasks.
- Confirm or reopen a drone.

Before rendering or fetching:

- Compute visible modules from the central access map.
- Do not call inventory/production endpoints for Sales or After-Sales users when they cannot use them.
- Remove the current red `Missing permission` workflow behavior.
- Omit inaccessible navigation and module sections entirely.

### Phase 4 — Role-specific workspaces

#### Managing Director

Add company-wide attention items, attendance exceptions, low stock, production bottlenecks, audit activity, and links into all permitted modules.

#### Production Manager

Add production-first tabs or segmented views:

- Active drones.
- Tasks and technician assignment.
- Component issues.
- Completion checklist and reopen flow.
- Installation traceability.

#### Store Manager

Add inventory-first views:

- Stock health.
- Opening inventory intake.
- Request review queue.
- Guided handover with quantity, availability, serials, and substitution approval.
- Missing-serial queue.
- Returned/damaged stock queue.
- Separate mailbox route.

#### Technician

Prioritize:

- My tasks.
- My component requests.
- Held components and missing serials.
- Relevant installation actions.
- Compact attendance.

Keep catalog content behind a secondary reference tab.

#### After-Sales Manager

Render only a deliberate empty state:

- `After-sales workspace is not enabled yet`.
- Explanation that the role is reserved for a future module.
- Link to personal attendance.
- Optional administrator/help action.

Never render production/inventory errors or trigger inaccessible requests.

### Phase 5 — Sales workspace boundary

Create `/dashboard/sales` and its polished placeholder:

- Customers.
- Quotations.
- Orders.
- Deliveries.
- Sold-drone records.

Until the API is available, show `Sales workspace coming next` with the intended areas and no production workflow content or permission error.

When Sales APIs are approved, add separate backend migrations, schemas, RBAC permissions, routers, and frontend data hooks. Do not fabricate sales KPIs from production data.

### Phase 6 — Global search and activity details

Add a debounced global search surface for:

- Drone serial.
- Component serial.
- Component request.
- Customer.
- Order.

Initially connect only to existing inventory/production endpoints or a new read-only search endpoint. Customer/order search remains disabled until Sales APIs exist.

Add readable detail links and remove UUIDs from primary tables. UUIDs may remain in secondary detail views for support/audit purposes.

### Phase 7 — Quality, accessibility, and responsive hardening

Implement:

- Skeletons for initial loads.
- Inline retryable error states.
- Intentional empty states.
- Confirmation dialogs for reject, cancel, mark damaged, reopen, and send.
- Sticky table headers where helpful.
- Responsive horizontal table scrolling.
- Accessible labels, focus order, keyboard support, and semantic landmarks.
- URL state for module tabs and important filters.

### Phase 8 — Verification and rollout

Run for all six seeded accounts:

- Login and dashboard landing.
- Visible navigation.
- KPI and quick-action relevance.
- No red permission errors.
- No forbidden API requests.
- Role-specific module access.
- Attendance self-view.
- Mailbox access only for Managing Director and Store Manager.
- After-Sales reserved-role empty state.

Verify at 390px and 1440px widths, then run:

- API tests.
- Ruff.
- Next.js production build.
- Frontend unit/component tests.
- Playwright role matrix tests.

## 6. API gaps discovered

The current API routers are:

- Admin.
- Attendance.
- Dashboard.
- Email.
- Inventory.
- Production.
- Current user.

There are no Sales endpoints or data models for:

- Customers.
- Quotations.
- Orders.
- Deliveries.
- Sold-drone records.

Therefore Phase 5 must initially be a frontend coming-soon workspace. Sales implementation will require a separate backend slice and should not block the shell redesign.

Additional likely API support for the redesign:

- A permission-filtered needs-attention endpoint or expanded dashboard summary response.
- Human-readable activity entities rather than audit rows containing only IDs/codes.
- Read-only global search endpoint.
- Optional dashboard date-range parameters.
- Low-stock and return/damaged aggregates if not already available from inventory queries.

## 7. File change map

Primary files to refactor:

- `apps/web/app/dashboard/page.tsx`
- `apps/web/app/globals.css`
- `apps/web/components/operational-dashboard.tsx`
- `apps/web/components/workflow-panel.tsx`
- `apps/web/components/attendance-panel.tsx`
- `apps/web/components/email-panel.tsx`

New frontend files should be composed around the shell, access map, overview, modules, and reusable states rather than adding more logic to `workflow-panel.tsx`.

## 8. Implementation status after the second audit

The first redesign phases are already implemented: the responsive shell, role-aware overview, focused routes, permission-safe loading, shadcn/ui foundation, separated Inventory/Production modules, Team administration, role-specific views, and six-role Playwright coverage are in place.

The next work is a hardening pass. The second audit identified several issues that affect trust and usability, so reliability and data correctness must be completed before additional visual refinement.

### Already implemented

- Central workspace configuration and role-aware navigation.
- Overview control tower with role-specific KPI selection, attention items, activity, and quick actions.
- Focused routes for Overview, Inventory, Production, Attendance, Mailbox, Sales, and Team.
- Permission-safe module rendering and scoped workflow data loading.
- Inventory and Production dialog-based workflow actions.
- Responsive shell and dense-table handling.
- Team administration with six approved roles.
- Six-role Playwright route/visibility matrix and an opt-in serialized workflow test.

### Remaining P0 work

1. **Reliable loading and retryable failures**

   Files:

   - `apps/web/lib/api-client.ts`
   - `apps/web/components/role-overview.tsx`
   - `apps/web/app/api/backend/[...path]/route.ts`
   - reusable `apps/web/components/error-state.tsx`

   Implementation:

   - Add an 8–10 second `AbortController` timeout to browser-side data requests.
   - Add an upstream timeout and explicit 502/504 JSON handling in the Next.js API proxy.
   - Preserve the last successful data during refresh.
   - Replace indefinite loading with a retryable `Operational data is unavailable` state.
   - Add tests for API stopped, delayed response, retry, and refresh-with-existing-data.

2. **Make the top-bar controls honest**

   Files:

   - `apps/web/components/app-shell.tsx`
   - `apps/web/components/role-overview.tsx`
   - new `apps/web/components/global-search.tsx` or a clearly disabled replacement.

   Implementation:

   - Wire refresh to the active route/module callback and keep the control visible only when it works.
   - Either implement a real search route or label the control as unavailable/coming soon. Do not leave an active input with no behavior.
   - The first search slice should cover drone serial, component serial, and component request. Customer/order search remains disabled until Sales APIs exist.

3. **Correct metric scope and human-readable data**

   Backend/API work:

   - Add correctly scoped dashboard fields such as `my_held_components` and `company_attendance_days`, or rename current cards to state their actual scope.
   - Add related display fields to request, installation, task, activity, and team responses: drone serial, component code/name, request reference, display name, and mailbox subject where available.
   - Keep UUIDs for secondary audit/detail views only.

   Frontend work:

   - Remove truncated UUID fallbacks from primary tables.
   - Replace generic `Component`, `Pending`, and `Operational activity` copy with readable names and meaningful statuses.
   - Add API tests for the new response fields and role-scoped metrics.

## 9. Remaining implementation order

### Phase 3A — Reliability foundation

Complete P0 items in this order:

1. Introduce shared request timeout/error utilities.
2. Harden the Next.js backend proxy.
3. Add reusable `ErrorState` and preserve stale data during refresh.
4. Wire or remove the top-bar refresh control.
5. Decide the smallest real global-search slice; implement it only if the API can support it cleanly.
6. Add automated tests for timeout, retry, and no-unnecessary-request behavior.

Exit criteria: stopping FastAPI produces a visible retryable error within 10 seconds; refreshing loaded data does not blank the page; no active control is inert.

Current decision/status:

- The top-bar refresh control is implemented through a client-side workspace refresh event consumed by the active Overview, Inventory/Production, Attendance, Mailbox, and Team panels.
- Global search is explicitly disabled as `Search coming soon` until a permission-safe V1 search projection exists for drone serials, component serials, and component requests. Customer/order search remains outside the current API scope.

### Phase 3B — Data trust and API display projections

1. Extend dashboard summary responses with accurate personal/company scopes.
2. Add human-readable related fields to inventory, production, audit, and team responses.
3. Centralize activity-action metadata in a shared map covering:
   - component requests and issues;
   - installation, removal, replacement, return, and damage;
   - production tasks and drone confirmation/reopen;
   - attendance actions and corrections;
   - mailbox connection, send, and read actions;
   - user/device administration.
4. Update `ActivityList`, request-review rows, installation history, and Team rows to consume those projections.

Exit criteria: no primary surface displays a UUID fragment or generic activity label when a readable value exists, and every KPI states the correct scope.

### Phase 3C — Route hierarchy and responsive overview

1. Remove duplicate route/module headers from Inventory and Production.
2. Keep one `ModuleHeader` per route with title, purpose, refresh, and primary action.
3. Simplify the overview header at widths below 768px: greeting first, subtitle second, date context as metadata below it.
4. Show the role label once and rename repeated overview-card headings to `Today’s overview`.
5. Verify exact layouts at 390px and 1440px.

### Phase 4A — Store Manager workspace

1. Put stock health, request review, pending handover, missing serials, and damaged/returned queues before reference content.
2. Move the full catalog into a secondary Catalog tab or collapsible section.
3. Add low-stock/zero-stock indicators using the seeded `minimum_stock` value.
4. Keep opening inventory as a focused intake flow with an intentional empty state instead of a large unexplained blank row.
5. Preserve issue, substitution, rejection, cancellation, and serial-entry behavior.

### Phase 4B — Production workspace

Add a compact status strip and URL-backed tabs/filters:

- Active drones.
- Tasks.
- Component issues.
- Traceability.
- Completion.

Each view gets a role-appropriate empty state, status filters, readable drone/component values, and dialogs for create/reopen/destructive actions.

### Phase 4C — Technician and After-Sales views

- Technician: tasks first, then requests, held/missing-serial components, relevant installation history, and compact attendance.
- After-Sales: intentional reserved-role empty state with personal attendance link; no inaccessible requests or red permission errors.

### Phase 5 — Authentication and administration polish

1. Restyle `apps/web/app/login/page.tsx` with the GOAG visual system, field states, loading, and inline errors.
2. Make `/` either a branded entry page or an authenticated redirect with a clear sign-in CTA.
3. Add a confirmation dialog for Team `Reset device`, with member-specific success/error feedback.
4. Preserve existing audit logging and recovery behavior.

### Phase 6 — Test-data isolation and acceptance verification

1. Keep Playwright records isolated with a dedicated company or clearly resettable fixture dataset; never hide them with frontend name filters.
2. Document the development fixture/reset procedure.
3. Run the complete six-role matrix with API request assertions.
4. Test API stopped and delayed states.
5. Verify mailbox access only for Managing Director and Store Manager.
6. Verify 390px and 1440px screenshots/flows.

## 10. Verification commands and release gate

Run from the repository root:

```bash
apps/api/.venv/bin/pytest apps/api/tests/test_foundation.py
apps/api/.venv/bin/ruff check apps/api/app apps/api/tests/test_foundation.py
pnpm --dir apps/web build
pnpm exec playwright test apps/web/tests/role-matrix.spec.ts
```

Run the data-writing workflow only when explicitly intended:

```bash
GOAG_TEST_PASSWORD=123456 \
GOAG_E2E_WORKFLOW=1 \
pnpm exec playwright test apps/web/tests/workflow-e2e.spec.ts
```

The redesign is ready for broader pilot review only when:

- all P0 items are resolved;
- all six role views pass without forbidden requests or red permission errors;
- metrics and activity labels are scope-accurate;
- no primary view exposes UUID fragments;
- API tests, lint, build, and Playwright coverage pass;
- the development fixture data is separated from visual-review data.

Backend files should only change when a frontend requirement cannot be fulfilled using an existing protected API. Any new endpoint must retain company scoping, RBAC dependencies, audit logging where it changes state, and test coverage.

## 11. Definition of done

The redesign is complete when:

- The dashboard is a role-aware control tower rather than a long form page.
- Navigation contains only accessible modules.
- No inaccessible module triggers a data request.
- All six seeded roles have a useful overview or intentional empty state.
- Managing Director, Production Manager, Store Manager, Technician, and After-Sales views match the approved brief.
- Sales has a polished workspace boundary and clearly documented API gap.
- No raw role codes, permission counts, UUIDs, `Module 2`, or `V1 modules` appear in primary UI.
- Existing inventory, production, attendance, mailbox, and authentication behavior remains functional.
- API tests, linting, production build, accessibility checks, and role-based Playwright tests pass.

## 12. Post-implementation audit findings — 2026-10-09

The first implementation pass now has the shell, role-aware navigation, route boundaries, role overviews, Sales placeholder, and After-Sales empty state. A live review of all seeded roles found the following remaining work. The detailed product/design instructions are in `FRONTEND_REDESIGN_PROMPT.md`; these are the implementation blockers that must be tracked.

### Priority 0

1. Add request timeouts and retryable error states. `RoleOverview` can sit on `Loading workspace` indefinitely when `/dashboard/summary` is slow, and `app/api/backend/[...path]/route.ts` has no upstream timeout or catch block.
2. Wire or remove the `AppShell` refresh icon. Implement global search or mark it unavailable; both currently look interactive but have no behavior.
3. Correct KPI scope. Technician `Held components` currently maps to company-wide `inventory_issued`; Managing Director `Attendance days` maps to personal attendance despite a company-wide subtitle.
4. Stop rendering UUID fragments in request tables, team tables, and workflow fallbacks. Enrich protected API responses with readable serials/names instead.

### Priority 1

1. Remove the duplicate route/module headers and the developer-facing `Role-filtered workspace` label.
2. Fix narrow-header wrapping and repeated role labels at mobile widths.
3. Complete the audit-action label map and show readable entities/statuses instead of `Operational activity` and `Recorded`.
4. Reorder the Store Manager workspace so request review, handover, missing serials, and stock health appear before the full catalog; add minimum-stock status.
5. Isolate `PW-E2E-*` fixture records from the visual-review/demo company.
6. Add production status filters/tabs so traceability, tasks, issues, and completion are not one long undifferentiated page.
7. Redesign the raw-HTML login and technical home pages to match the workspace visual system.
8. Add confirmation and success/error feedback to Team & admin device reset.

Do not mark the frontend redesign complete until the second-audit checklist in `FRONTEND_REDESIGN_PROMPT.md` passes for all six seeded roles.

## 13. Plan review addendum — drawbacks and corrections

This addendum records risks in the plan itself. These are execution risks, not additional visual polish. Resolve them before treating the plan as a reliable delivery checklist.

### 1. The plan can cause duplicated or unnecessary work

The earlier phases describe creating files and components that already exist, while the later status section says those phases are implemented. An agent following the document from the top could rebuild the shell or split workflow components a second time.

Correction:

- Start implementation from Section 8 and the remaining order in Section 9.
- Treat Sections 1–7 as context and acceptance intent, not a fresh task list.
- Before editing, inspect the current source and keep existing working behavior unless a later P0/P1 item explicitly replaces it.

### 2. The current automated role coverage is weaker than the release gate claims

`apps/web/tests/role-matrix.spec.ts` skips every authenticated role when password environment variables are missing. It also verifies visible text, but does not currently assert that forbidden API requests were not made. The plan says all six roles and forbidden-request checks must pass, so a green test run can currently mean that the important role tests were skipped.

Correction:

- Add a clearly named acceptance command, such as `GOAG_RUN_ROLE_MATRIX=1 pnpm exec playwright test apps/web/tests/role-matrix.spec.ts`.
- When that command is used, fail fast if any required role credential is missing; do not silently skip.
- Add Playwright request interception/logging and assert that Sales and After-Sales do not call inventory, production, mailbox, or team endpoints they cannot access.
- Report the number of skipped role tests in CI output and do not call the matrix complete when any required role is skipped.
- Keep a separate unauthenticated/public test path if credentials cannot be stored in CI.

### 3. Failure-state testing is underspecified for the current Playwright setup

The Playwright config automatically starts or reuses FastAPI. “Stop FastAPI and test the UI” is therefore not a deterministic test instruction; the web server fixture may start it again, and a hanging upstream request can make the test itself hang.

Correction:

- Test API failure at the browser boundary by routing `/api/backend/**` to a controlled 503 response and by delaying a response beyond the client timeout.
- Add one integration test for the real proxy timeout separately from the client error-state test.
- Use explicit test timeouts and assert the retry UI appears within 10 seconds.
- Keep destructive/data-writing workflow tests separate from read-only UI and failure-state tests.

### 4. Refresh/search architecture is not defined for a server-rendered shell

`AppShell` is currently a server component, but the plan asks it to own `router.refresh()` and module refresh callbacks. The agent should not attach client event handlers directly to a server component.

Correction:

- Keep `AppShell` as a server-safe layout component and extract a small client `TopBar`/`WorkspaceControls` component for refresh, search, and user-menu interactions.
- Pass only serializable route/access data into that client component.
- Use a shared refresh contract (`onRefresh` or a route refresh event) for client modules; do not rely on a full browser reload that loses filters or open dialogs.

### 5. Global search can expand scope without a clear V1 boundary

The plan mentions drone serials, component serials, requests, customers, and orders, but customer/order APIs do not exist. Implementing the full search bar before those contracts exist risks creating a misleading global search experience and delaying the core role work.

Correction:

- V1 search scope is only drone serial, component serial, and component request.
- Make customer/order entries visibly unavailable until Sales APIs exist.
- If the backend cannot support the V1 search cleanly, replace the active input with a disabled `Search is coming soon` control and remove it from the release gate.
- Define the response shape, permission filtering, empty state, keyboard behavior, and URL/deep-link behavior before implementation.

### 6. The API projection work needs explicit ownership and compatibility rules

The plan correctly identifies that readable serials, names, and accurate metric scopes may require backend changes, but it does not say which existing response contracts may change or how clients stay compatible.

Correction:

- For every new dashboard/activity field, document the endpoint, schema, permission scope, and fallback behavior before editing the UI.
- Prefer additive response fields over breaking changes to existing API shapes.
- Add backend tests for company scoping, role scoping, and missing related records.
- Never compute company-wide or user-specific metrics from a broader response in the browser.
- If a projection is not available yet, hide the KPI or label it honestly instead of showing an approximate value.

### 7. Test-data isolation is a release prerequisite, not a cleanup task

The workflow E2E test writes drones, components, requests, tasks, and installation records. If it shares the visual-review company, the UI will keep accumulating `PW-E2E-*` records and acceptance screenshots will become less meaningful.

Correction:

- Run data-writing E2E tests against a dedicated test company/database or a deterministic resettable fixture namespace.
- Do not filter records by `PW-E2E` in the frontend.
- Add a documented reset command and run it before visual-review screenshots.
- Make read-only role tests safe to run repeatedly against the demo dataset.

### 8. Some planned deliverables are named but not yet present

The plan references `error-state.tsx`, `module-header.tsx`, `status-badge.tsx`, `PermissionGate`, and `RoleGate`, but the current source tree does not contain all of these primitives. The plan should distinguish “required missing deliverable” from “already implemented equivalent.”

Correction:

- Create the missing primitives only where they remove duplication or enforce consistent behavior.
- If an existing equivalent is intentionally used, rename the plan entry to the actual file and document the equivalence.
- Do not create wrappers that merely add another abstraction around the current scattered `can()` checks; centralize access decisions first.

### 9. Accessibility and visual verification are named but not measurable

The plan asks for accessibility checks and 390px/1440px verification, but the current test setup has no explicit accessibility tool or visual regression assertion.

Correction:

- Add deterministic Playwright checks for keyboard reachability, visible focus, dialog escape/close, semantic headings, labels, and mobile navigation.
- Add an accessibility scan using the project-approved tool or document the manual checklist if adding a dependency is not desired.
- Capture a small role-by-viewport verification set: Managing Director, Store Manager, Technician, and After-Sales at 390px and 1440px; the full matrix still verifies route/content behavior.
- Treat screenshots as evidence for layout review, not as the only correctness signal.

### 10. The release gate needs a typecheck and a no-regression data gate

The current root scripts expose build, lint, and Playwright commands, but there is no explicit frontend typecheck command. The release gate also does not explicitly prove that existing workflow behavior remains functional after the redesign.

Correction:

- Run `pnpm --dir apps/web exec tsc --noEmit` in addition to the production build.
- Keep the serialized workflow E2E test as a required, isolated regression test when `GOAG_E2E_WORKFLOW=1` is enabled.
- Add read-only assertions for inventory, production, attendance, mailbox RBAC, and authentication routes.
- Record whether the workflow test ran or was intentionally omitted; do not report the full release gate as complete when it was skipped.

## 14. Revised release gate

The release gate is split into mandatory local checks and environment-dependent checks. A missing credential or isolated test environment is a failed prerequisite, not a successful skip.

### Mandatory local gate

- Section 9 P0 work is complete.
- Refresh and search are functional or explicitly unavailable, never inert.
- New API projections have backend permission/company-scope tests.
- UUID fragments, inaccurate KPI labels, generic activity copy, and test fixtures are absent from primary UI surfaces.
- Typecheck, API tests, Ruff, production build, and deterministic client/proxy failure tests pass.

The deterministic client failure command is:

```bash
GOAG_E2E_FAILURES=1 GOAG_TEST_PASSWORD=123456 \
pnpm exec playwright test apps/web/tests/failure-state.spec.ts
```

### Environment-dependent acceptance gate

- All six role credentials are present and the authenticated role matrix runs with zero required skips.
- Forbidden API request assertions pass for Sales and After-Sales.
- API stopped/slow-response tests show a retryable state within 10 seconds.
- Accessibility checks and the 390px/1440px role viewport checks pass.
- The data-writing workflow test runs against isolated/resettable data and passes.

If an environment-dependent check cannot run, report the release as `unverified` with the missing prerequisite; never report it as complete.
