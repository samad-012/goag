"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { InventoryModule } from "@/components/inventory-module";
import { ProductionModule } from "@/components/production-module";
import type { ReopenState, ReviewState } from "@/components/workflow-review-dialogs";
import { WORKSPACE_REFRESH_EVENT } from "@/lib/workspace-events";
import type { ActionForm, Component, ComponentRequest, Drone, DroneForm, DroneModel, Installation, InventoryUnit, IssueForm, ProductionTask, RequestForm, TaskForm } from "@/components/workflow-types";

const createNewValue = "__new__";

function suggestedCode(value: string) {
  return value.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 100);
}

async function workflowRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

type WorkflowScope = "inventory" | "production";

export function WorkflowPanel({ permissions, roleCodes, scope }: { permissions: string[]; roleCodes: string[]; scope: WorkflowScope }) {
  const [components, setComponents] = useState<Component[]>([]);
  const [droneModels, setDroneModels] = useState<DroneModel[]>([]);
  const [drones, setDrones] = useState<Drone[]>([]);
  const [requests, setRequests] = useState<ComponentRequest[]>([]);
  const [units, setUnits] = useState<InventoryUnit[]>([]);
  const [installations, setInstallations] = useState<Installation[]>([]);
  const [tasks, setTasks] = useState<ProductionTask[]>([]);
  const [assignees, setAssignees] = useState<{ membership_id: string; display_name: string; email: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [droneForm, setDroneForm] = useState<DroneForm>({ drone_model_id: "", new_model_name: "", new_model_code: "", serial_number: "", notes: "" });
  const [requestForm, setRequestForm] = useState<RequestForm>({ drone_id: "", component_id: "", new_component_name: "", new_component_code: "", new_component_category: "", quantity: "1" });
  const [issueForm, setIssueForm] = useState<IssueForm>({ request_item_id: "", quantity: "1", serial_numbers: "", substituted_component_id: "" });
  const [issueDialogOpen, setIssueDialogOpen] = useState(false);
  const [serialDraft, setSerialDraft] = useState<Record<string, string>>({});
  const [actionForm, setActionForm] = useState<ActionForm>({ drone_id: "", inventory_unit_id: "", action: "install", replacement_for_id: "", reason: "" });
  const [confirmationDroneId, setConfirmationDroneId] = useState("");
  const [confirmationDialogOpen, setConfirmationDialogOpen] = useState(false);
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [reviewState, setReviewState] = useState<ReviewState>(null);
  const [reviewReason, setReviewReason] = useState("");
  const [approvalInstallationId, setApprovalInstallationId] = useState<string | null>(null);
  const [taskForm, setTaskForm] = useState<TaskForm>({ drone_id: "", title: "", assigned_to_membership_id: "", notes: "" });
  const [reopenDroneId, setReopenDroneId] = useState("");
  const [reopenState, setReopenState] = useState<ReopenState>(null);

  const can = (permission: string) => permissions.includes(permission);
  const showInventory = scope === "inventory";
  const showProduction = scope === "production";

  const loadData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError("");
    const results = await Promise.allSettled([
      can("inventory.read") ? workflowRequest<Component[]>("/inventory/components") : Promise.resolve([]),
      showProduction ? workflowRequest<DroneModel[]>("/production/drone-models") : Promise.resolve([]),
      can("drone.read") && (showProduction || can("request.create") || can("request.read_all")) ? workflowRequest<Drone[]>("/production/drones") : Promise.resolve([]),
      showInventory || can("component.install") ? workflowRequest<InventoryUnit[]>("/inventory/units") : Promise.resolve([]),
      can("request.read_all") ? workflowRequest<ComponentRequest[]>("/inventory/component-requests") : Promise.resolve([]),
      showProduction && can("drone.read") ? workflowRequest<Installation[]>("/production/component-installations") : Promise.resolve([]),
      can("drone.read") ? workflowRequest<ProductionTask[]>("/production/tasks") : Promise.resolve([]),
      showProduction && can("assignment.manage") ? workflowRequest<{ membership_id: string; display_name: string; email: string }[]>("/production/assignees") : Promise.resolve([]),
    ]);
    const [componentResult, modelResult, droneResult, unitResult, requestResult, installationResult, taskResult, assigneeResult] = results;
    if (componentResult.status === "fulfilled") setComponents(componentResult.value);
    if (modelResult.status === "fulfilled") setDroneModels(modelResult.value);
    if (droneResult.status === "fulfilled") setDrones(droneResult.value);
    if (unitResult.status === "fulfilled") setUnits(unitResult.value);
    if (requestResult.status === "fulfilled") setRequests(requestResult.value);
    if (installationResult.status === "fulfilled") setInstallations(installationResult.value);
    if (taskResult.status === "fulfilled") setTasks(taskResult.value);
    if (assigneeResult.status === "fulfilled") setAssignees(assigneeResult.value);
    const failed = results.find((result) => result.status === "rejected");
    const hasLoadedData = results.some((result) => result.status === "fulfilled" && Array.isArray(result.value) && result.value.length > 0);
    if (failed?.status === "rejected" && !hasLoadedData) setError(failed.reason instanceof Error ? failed.reason.message : "Unable to load workflow data.");
    setLoading(false);
  };

  useEffect(() => {
    void loadData();
    const refresh = () => void loadData();
    window.addEventListener(WORKSPACE_REFRESH_EVENT, refresh);
    return () => window.removeEventListener(WORKSPACE_REFRESH_EVENT, refresh);
    // Permissions and scope are fixed for the authenticated dashboard session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const componentById = useMemo(() => new Map(components.map((component) => [component.id, component])), [components]);
  const droneById = useMemo(() => new Map(drones.map((drone) => [drone.id, drone])), [drones]);
  const unitById = useMemo(() => new Map(units.map((unit) => [unit.id, unit])), [units]);
  const openRequestItems = useMemo(() => requests.flatMap((request) => request.items.filter((item) => item.pending_quantity > 0).map((item) => ({ request, item }))), [requests]);

  const run = async (operation: () => Promise<void>, successMessage: string): Promise<boolean> => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await operation();
      await loadData();
      setMessage(successMessage);
      return true;
    } catch (operationError) {
      setError(operationError instanceof Error ? operationError.message : "The operation failed.");
      return false;
    } finally {
      setBusy(false);
    }
  };

  const createDrone = async (event: FormEvent) => {
    event.preventDefault();
    await run(async () => {
      let droneModelId = droneForm.drone_model_id || null;
      if (droneForm.drone_model_id === createNewValue) {
        const modelName = droneForm.new_model_name.trim();
        const modelCode = droneForm.new_model_code.trim() || suggestedCode(modelName);
        if (!modelName || !modelCode) throw new Error("Enter a name for the new drone model.");
        const model = await workflowRequest<DroneModel>("/production/drone-models", { method: "POST", body: JSON.stringify({ name: modelName, code: modelCode }) });
        droneModelId = model.id;
      }
      const drone = await workflowRequest<Drone>("/production/drones", { method: "POST", body: JSON.stringify({ serial_number: droneForm.serial_number, notes: droneForm.notes, drone_model_id: droneModelId }) });
      setDrones((current) => [drone, ...current]);
      setDroneForm({ drone_model_id: "", new_model_name: "", new_model_code: "", serial_number: "", notes: "" });
    }, "Drone record created.");
  };

  const createRequest = async (event: FormEvent) => {
    event.preventDefault();
    await run(async () => {
      let componentId = requestForm.component_id;
      if (requestForm.component_id === createNewValue) {
        if (!can("inventory.catalog.manage")) throw new Error("You do not have permission to add a new component to the catalog.");
        const componentName = requestForm.new_component_name.trim();
        const componentCode = requestForm.new_component_code.trim() || suggestedCode(componentName);
        const componentCategory = requestForm.new_component_category.trim();
        if (!componentName || !componentCode || !componentCategory) throw new Error("Enter the new component name and category.");
        const component = await workflowRequest<Component>("/inventory/components", { method: "POST", body: JSON.stringify({ code: componentCode, name: componentName, category: componentCategory, serialized: true }) });
        componentId = component.id;
      }
      const request = await workflowRequest<ComponentRequest>("/inventory/component-requests", { method: "POST", body: JSON.stringify({ drone_id: requestForm.drone_id, items: [{ component_id: componentId, requested_quantity: Number(requestForm.quantity) }] }) });
      setRequests((current) => [request, ...current]);
      setRequestForm({ drone_id: "", component_id: "", new_component_name: "", new_component_code: "", new_component_category: "", quantity: "1" });
    }, "Component request submitted.");
  };

  const issueComponent = async (event: FormEvent) => {
    event.preventDefault();
    const succeeded = await run(async () => {
      const serialNumbers = issueForm.serial_numbers.split(/[\n,]/).map((serial) => serial.trim()).filter(Boolean);
      await workflowRequest(`/inventory/component-requests/${issueForm.request_item_id.split("|")[0]}/issue`, { method: "POST", body: JSON.stringify({ lines: [{ request_item_id: issueForm.request_item_id.split("|")[1], quantity: Number(issueForm.quantity), serial_numbers: serialNumbers, ...(issueForm.substituted_component_id ? { substituted_component_id: issueForm.substituted_component_id } : {}) }] }) });
      setIssueForm({ request_item_id: "", quantity: "1", serial_numbers: "", substituted_component_id: "" });
    }, "Component quantity issued; remaining quantity stays pending when applicable.");
    if (succeeded) setIssueDialogOpen(false);
  };

  const assignSerial = async (unit: InventoryUnit) => {
    const serial = serialDraft[unit.id]?.trim();
    if (!serial) return;
    await run(async () => {
      await workflowRequest(`/inventory/units/${unit.id}/serial`, { method: "PATCH", body: JSON.stringify({ serial_number: serial }) });
      setSerialDraft((current) => ({ ...current, [unit.id]: "" }));
    }, "Component serial number recorded.");
  };

  const componentAction = async (event: FormEvent) => {
    event.preventDefault();
    await run(async () => {
      await workflowRequest(`/production/drones/${actionForm.drone_id}/components`, { method: "POST", body: JSON.stringify({ action: actionForm.action, inventory_unit_id: actionForm.inventory_unit_id, ...(actionForm.replacement_for_id ? { replacement_for_id: actionForm.replacement_for_id } : {}), ...(actionForm.reason ? { reason: actionForm.reason } : {}) }) });
    }, "Component action recorded in the traceability history.");
  };

  const confirmDrone = async (event: FormEvent) => {
    event.preventDefault();
    const succeeded = await run(async () => {
      await workflowRequest(`/production/drones/${confirmationDroneId}/confirm`, { method: "POST", body: JSON.stringify({ checklist: checks }) });
    }, "Drone confirmed and locked against normal edits.");
    if (succeeded) setConfirmationDialogOpen(false);
  };

  const prepareIssue = (request: ComponentRequest) => {
    const item = request.items.find((requestItem) => requestItem.pending_quantity > 0);
    if (!item) return;
    setIssueForm((current) => ({ ...current, request_item_id: `${request.id}|${item.id}`, quantity: String(item.pending_quantity) }));
    setIssueDialogOpen(true);
  };

  const submitReviewAction = async (event: FormEvent) => {
    event.preventDefault();
    if (!reviewState || !reviewReason.trim()) return;
    const succeeded = await run(async () => {
      await workflowRequest(`/inventory/component-requests/${reviewState.requestId}/${reviewState.action}`, { method: "POST", body: JSON.stringify({ reason: reviewReason.trim() }) });
    }, reviewState.action === "reject" ? "Component request rejected and audit logged." : "Remaining request quantity cancelled and audit logged.");
    if (succeeded) { setReviewState(null); setReviewReason(""); }
  };

  const approveInstallation = async (installationId: string) => {
    const succeeded = await run(async () => {
      await workflowRequest(`/production/component-installations/${installationId}/approve`, { method: "POST" });
    }, "Component action approved and added to the audit history.");
    if (succeeded) setApprovalInstallationId(null);
  };

  const createTask = async (event: FormEvent) => {
    event.preventDefault();
    await run(async () => {
      await workflowRequest(`/production/drones/${taskForm.drone_id}/tasks`, { method: "POST", body: JSON.stringify({ title: taskForm.title, assigned_to_membership_id: taskForm.assigned_to_membership_id || null, notes: taskForm.notes || null }) });
      setTaskForm({ drone_id: "", title: "", assigned_to_membership_id: "", notes: "" });
    }, "Production task created.");
  };

  const updateTask = async (task: ProductionTask, status: "open" | "in_progress" | "completed" | "cancelled") => {
    await run(async () => {
      await workflowRequest(`/production/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ status, notes: task.notes }) });
    }, `Task marked ${status.replace("_", " ")}.`);
  };

  const submitReopen = async (event: FormEvent) => {
    event.preventDefault();
    if (!reopenState?.reason.trim()) return;
    const succeeded = await run(async () => {
      await workflowRequest(`/production/drones/${reopenState.droneId}/reopen`, { method: "POST", body: JSON.stringify({ reason: reopenState.reason.trim() }) });
    }, "Drone reopened. The reason was recorded in the audit history.");
    if (succeeded) setReopenState(null);
  };

  const notices = <>{message && <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div>}{error && <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">{error}</div>}</>;

  if (loading) return <Card><CardContent className="py-8 text-sm text-muted-foreground">Loading {scope} workspace…</CardContent></Card>;

  if (scope === "inventory") return <section className="space-y-6" aria-label="Inventory workspace">{notices}<InventoryModule roleCodes={roleCodes} components={components} units={units} drones={drones} requests={requests} tasks={tasks} componentById={componentById} droneById={droneById} openRequestItems={openRequestItems} busy={busy} can={can} requestForm={requestForm} setRequestForm={setRequestForm} issueForm={issueForm} setIssueForm={setIssueForm} issueDialogOpen={issueDialogOpen} setIssueDialogOpen={setIssueDialogOpen} serialDraft={serialDraft} setSerialDraft={setSerialDraft} reviewState={reviewState} reviewReason={reviewReason} setReviewReason={setReviewReason} onOpeningInventorySaved={() => void loadData(false)} onCreateRequest={createRequest} onIssueComponents={issueComponent} onAssignSerial={(unit) => void assignSerial(unit)} onPrepareIssue={prepareIssue} onRejectRequest={(requestId) => { setReviewState({ requestId, action: "reject" }); setReviewReason(""); }} onCancelRequest={(requestId) => { setReviewState({ requestId, action: "cancel" }); setReviewReason(""); }} onReviewChange={(open) => { if (!open) { setReviewState(null); setReviewReason(""); } }} onSubmitReview={submitReviewAction} /></section>;

  return <section className="space-y-6" aria-label="Production workspace">{notices}<ProductionModule roleCodes={roleCodes} components={components} droneModels={droneModels} drones={drones} units={units} installations={installations} tasks={tasks} assignees={assignees} componentById={componentById} droneById={droneById} unitById={unitById} busy={busy} can={can} droneForm={droneForm} setDroneForm={setDroneForm} requestForm={requestForm} setRequestForm={setRequestForm} actionForm={actionForm} setActionForm={setActionForm} taskForm={taskForm} setTaskForm={setTaskForm} confirmationDroneId={confirmationDroneId} setConfirmationDroneId={setConfirmationDroneId} checks={checks} setChecks={setChecks} confirmationDialogOpen={confirmationDialogOpen} setConfirmationDialogOpen={setConfirmationDialogOpen} reopenDroneId={reopenDroneId} setReopenDroneId={setReopenDroneId} reopenState={reopenState} approvalInstallationId={approvalInstallationId} onApprovalChange={(open) => { if (!open) setApprovalInstallationId(null); }} onReviewApproval={setApprovalInstallationId} onCreateDrone={createDrone} onCreateRequest={createRequest} onComponentAction={componentAction} onCreateTask={createTask} onUpdateTask={(task, status) => void updateTask(task, status)} onConfirmDrone={confirmDrone} onApproveInstallation={(installationId) => void approveInstallation(installationId)} onOpenReopen={(droneId) => setReopenState({ droneId, reason: "" })} onReopenChange={(open) => { if (!open) setReopenState(null); }} onReopenReasonChange={(reason) => setReopenState((current) => current ? { ...current, reason } : current)} onSubmitReopen={submitReopen} /></section>;
}
