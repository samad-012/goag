"use client";

import { Dispatch, FormEvent, SetStateAction } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { InstallationApprovalDialog, ReopenDroneDialog, type ReopenState } from "@/components/workflow-review-dialogs";
import type { ActionForm, Assignee, Component, ComponentRequest, Drone, DroneForm, DroneModel, InventoryUnit, ProductionTask, RequestForm } from "@/components/workflow-types";
import { confirmationChecks, type ConfirmationCheck } from "@/components/workflow-types";

const fieldClassName = "h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring";
const createNewValue = "__new__";

type ProductionModuleProps = {
  roleCodes: string[];
  components: Component[];
  droneModels: DroneModel[];
  drones: Drone[];
  units: InventoryUnit[];
  installations: import("@/components/workflow-types").Installation[];
  tasks: ProductionTask[];
  assignees: Assignee[];
  componentById: Map<string, Component>;
  droneById: Map<string, Drone>;
  unitById: Map<string, InventoryUnit>;
  busy: boolean;
  can: (permission: string) => boolean;
  droneForm: DroneForm;
  setDroneForm: Dispatch<SetStateAction<DroneForm>>;
  requestForm: RequestForm;
  setRequestForm: Dispatch<SetStateAction<RequestForm>>;
  actionForm: ActionForm;
  setActionForm: Dispatch<SetStateAction<ActionForm>>;
  taskForm: import("@/components/workflow-types").TaskForm;
  setTaskForm: Dispatch<SetStateAction<import("@/components/workflow-types").TaskForm>>;
  confirmationDroneId: string;
  setConfirmationDroneId: (value: string) => void;
  checks: Record<string, boolean>;
  setChecks: Dispatch<SetStateAction<Record<string, boolean>>>;
  confirmationDialogOpen: boolean;
  setConfirmationDialogOpen: (open: boolean) => void;
  reopenDroneId: string;
  setReopenDroneId: (value: string) => void;
  reopenState: ReopenState;
  approvalInstallationId: string | null;
  onApprovalChange: (open: boolean) => void;
  onReviewApproval: (installationId: string) => void;
  onCreateDrone: (event: FormEvent) => void;
  onCreateRequest: (event: FormEvent) => void;
  onComponentAction: (event: FormEvent) => void;
  onCreateTask: (event: FormEvent) => void;
  onUpdateTask: (task: ProductionTask, status: "open" | "in_progress" | "completed" | "cancelled") => void;
  onConfirmDrone: (event: FormEvent) => void;
  onApproveInstallation: (installationId: string) => void;
  onOpenReopen: (droneId: string) => void;
  onReopenChange: (open: boolean) => void;
  onReopenReasonChange: (reason: string) => void;
  onSubmitReopen: (event: FormEvent) => void;
};

export function ProductionModule({
  roleCodes,
  components,
  droneModels,
  drones,
  units,
  installations,
  tasks,
  assignees,
  componentById,
  droneById,
  unitById,
  busy,
  can,
  droneForm,
  setDroneForm,
  requestForm,
  setRequestForm,
  actionForm,
  setActionForm,
  taskForm,
  setTaskForm,
  confirmationDroneId,
  setConfirmationDroneId,
  checks,
  setChecks,
  confirmationDialogOpen,
  setConfirmationDialogOpen,
  reopenDroneId,
  setReopenDroneId,
  reopenState,
  approvalInstallationId,
  onApprovalChange,
  onReviewApproval,
  onCreateDrone,
  onCreateRequest,
  onComponentAction,
  onCreateTask,
  onUpdateTask,
  onConfirmDrone,
  onApproveInstallation,
  onOpenReopen,
  onReopenChange,
  onReopenReasonChange,
  onSubmitReopen,
}: ProductionModuleProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const taskFilter = searchParams.get("task_status") ?? "all";
  const isTechnician = roleCodes.includes("TECHNICIAN");
  const focus = isTechnician
    ? { title: "Assigned production work", description: "View only tasks assigned to you, update their progress, and record component actions for your work." }
    : { title: "Production control", description: "Create drones, assign technicians, approve component actions, complete tasks, and confirm finished records." };
  const activeDroneCount = drones.filter((drone) => drone.status === "draft").length;
  const openTaskCount = tasks.filter((task) => !["completed", "cancelled"].includes(task.status)).length;
  const pendingApprovalCount = installations.filter((installation) => !installation.approved_by_membership_id).length;
  const confirmedDroneCount = drones.filter((drone) => drone.status === "confirmed").length;
  const visibleTasks = tasks.filter((task) => {
    if (taskFilter === "open") return task.status === "open";
    if (taskFilter === "in_progress") return task.status === "in_progress";
    if (taskFilter === "completed") return task.status === "completed";
    return true;
  });
  const setTaskFilter = (value: string) => {
    const next = new URLSearchParams(searchParams.toString());
    if (value === "all") next.delete("task_status");
    else next.set("task_status", value);
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };
  return (
    <div className="space-y-6" aria-label="Production workspace">
      <Card className="border-primary/15 bg-primary/[0.03]" size="sm">
        <CardContent className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="text-sm font-semibold">{focus.title}</p><p className="text-xs text-muted-foreground">{focus.description}</p></div>
          <Badge className="w-fit" variant="outline">Role-filtered workspace</Badge>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Production status summary">
        {[
          ["Active drones", activeDroneCount, "Draft records in production"],
          ["Open tasks", openTaskCount, "Open or in progress"],
          ["Pending approvals", pendingApprovalCount, "Component actions to review"],
          ["Confirmed drones", confirmedDroneCount, "Production records locked"],
        ].map(([label, value, detail]) => (
          <Card key={label} size="sm"><CardContent className="py-4"><p className="text-xs font-medium text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p><p className="text-xs text-muted-foreground">{detail}</p></CardContent></Card>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {can("drone.create") && <Dialog>
          <DialogTrigger asChild><Button type="button" variant="outline" className="h-auto min-h-24 justify-start text-left"><span><span className="block font-semibold">Create drone</span><span className="mt-1 block text-xs font-normal text-muted-foreground">Assign a model and serial number before production begins.</span></span></Button></DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader><DialogTitle>Create drone</DialogTitle><DialogDescription>Production managers assign the drone serial before confirmation.</DialogDescription></DialogHeader>
            <form className="space-y-3" onSubmit={onCreateDrone}>
              <div><Label htmlFor="production-drone-model">Drone model</Label><select id="production-drone-model" className={fieldClassName} required value={droneForm.drone_model_id} onChange={(event) => setDroneForm({ ...droneForm, drone_model_id: event.target.value })}><option value="">Select a model</option>{droneModels.map((model) => <option key={model.id} value={model.id}>{model.code} · {model.name}</option>)}<option value={createNewValue}>Model not listed — add new model</option></select></div>
              {droneForm.drone_model_id === createNewValue && <div className="grid gap-3 rounded-md border bg-muted/30 p-3 sm:grid-cols-2"><div><Label htmlFor="production-new-model-name">New model name</Label><Input id="production-new-model-name" required value={droneForm.new_model_name} onChange={(event) => setDroneForm({ ...droneForm, new_model_name: event.target.value })} placeholder="10X Pro" /></div><div><Label htmlFor="production-new-model-code">Model code <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="production-new-model-code" value={droneForm.new_model_code} onChange={(event) => setDroneForm({ ...droneForm, new_model_code: event.target.value })} placeholder="Auto-generated from name" /></div></div>}
              <div><Label htmlFor="production-drone-serial">Drone serial number</Label><Input id="production-drone-serial" required value={droneForm.serial_number} onChange={(event) => setDroneForm({ ...droneForm, serial_number: event.target.value })} placeholder="DRONE-2026-001" /></div>
              <div><Label htmlFor="production-drone-notes">Notes</Label><textarea id="production-drone-notes" className={`${fieldClassName} min-h-20 py-2`} value={droneForm.notes} onChange={(event) => setDroneForm({ ...droneForm, notes: event.target.value })} placeholder="Production notes" /></div>
              <DialogFooter><Button disabled={busy} type="submit">Create drone record</Button></DialogFooter>
            </form>
          </DialogContent>
        </Dialog>}

        {can("request.create") && <Dialog>
          <DialogTrigger asChild><Button type="button" variant="outline" className="h-auto min-h-24 justify-start text-left"><span><span className="block font-semibold">Request components</span><span className="mt-1 block text-xs font-normal text-muted-foreground">Submit a component request for an active drone.</span></span></Button></DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader><DialogTitle>Request components</DialogTitle><DialogDescription>Technicians and production can request parts for a drone.</DialogDescription></DialogHeader>
            <form className="space-y-3" onSubmit={onCreateRequest}>
              <div><Label htmlFor="production-request-drone">Drone</Label><select id="production-request-drone" className={fieldClassName} required value={requestForm.drone_id} onChange={(event) => setRequestForm({ ...requestForm, drone_id: event.target.value })}><option value="">Select a drone</option>{drones.filter((drone) => drone.status !== "confirmed").map((drone) => <option key={drone.id} value={drone.id}>{drone.serial_number ?? "Drone serial pending"}</option>)}</select></div>
              <div><Label htmlFor="production-request-component">Component</Label><select id="production-request-component" className={fieldClassName} required value={requestForm.component_id} onChange={(event) => setRequestForm({ ...requestForm, component_id: event.target.value })}><option value="">Select a component</option>{components.map((component) => <option key={component.id} value={component.id}>{component.code} · {component.name}</option>)}<option value={createNewValue}>Component not listed — add to catalog</option></select></div>
              {requestForm.component_id === createNewValue && <div className="grid gap-3 rounded-md border bg-muted/30 p-3 sm:grid-cols-2"><div><Label htmlFor="production-new-component-name">New component name</Label><Input id="production-new-component-name" required value={requestForm.new_component_name} onChange={(event) => setRequestForm({ ...requestForm, new_component_name: event.target.value })} placeholder="Flight controller" /></div><div><Label htmlFor="production-new-component-code">Component code <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="production-new-component-code" value={requestForm.new_component_code} onChange={(event) => setRequestForm({ ...requestForm, new_component_code: event.target.value })} placeholder="Auto-generated from name" /></div><div className="sm:col-span-2"><Label htmlFor="production-new-component-category">Category</Label><Input id="production-new-component-category" required value={requestForm.new_component_category} onChange={(event) => setRequestForm({ ...requestForm, new_component_category: event.target.value })} placeholder="Electronics" /></div></div>}
              <div><Label htmlFor="production-request-quantity">Quantity</Label><Input id="production-request-quantity" min="1" type="number" required value={requestForm.quantity} onChange={(event) => setRequestForm({ ...requestForm, quantity: event.target.value })} /></div>
              <DialogFooter><Button disabled={busy} type="submit">Submit request</Button></DialogFooter>
            </form>
          </DialogContent>
        </Dialog>}
      </div>

      {can("component.install") && <Dialog>
        <DialogTrigger asChild><Button type="button" variant="outline" className="h-auto min-h-24 w-full justify-start text-left"><span><span className="block font-semibold">Component traceability</span><span className="mt-1 block text-xs font-normal text-muted-foreground">Install, remove, replace, return, or mark a unit damaged.</span></span></Button></DialogTrigger>
        <DialogContent className="max-w-3xl">
          <DialogHeader><DialogTitle>Component traceability</DialogTitle><DialogDescription>Install, remove, replace, return, or mark an issued component damaged.</DialogDescription></DialogHeader>
          <form className="grid gap-3 md:grid-cols-2" onSubmit={onComponentAction}>
            <div><Label htmlFor="production-action-drone">Drone</Label><select id="production-action-drone" className={fieldClassName} required value={actionForm.drone_id} onChange={(event) => setActionForm({ ...actionForm, drone_id: event.target.value })}><option value="">Select a drone</option>{drones.map((drone) => <option key={drone.id} value={drone.id}>{drone.serial_number ?? "Drone serial pending"}</option>)}</select></div>
            <div><Label htmlFor="production-action-unit">Component unit</Label><select id="production-action-unit" className={fieldClassName} required value={actionForm.inventory_unit_id} onChange={(event) => setActionForm({ ...actionForm, inventory_unit_id: event.target.value })}><option value="">Select a unit</option>{units.filter((unit) => unit.serial_number).map((unit) => <option key={unit.id} value={unit.id}>{componentById.get(unit.component_id)?.code ?? "Component"} · {unit.serial_number} · {unit.status}</option>)}</select></div>
            <div><Label htmlFor="production-action-type">Action</Label><select id="production-action-type" className={fieldClassName} value={actionForm.action} onChange={(event) => setActionForm({ ...actionForm, action: event.target.value })}><option value="install">Install</option><option value="remove">Remove</option><option value="replace">Replace</option><option value="return">Return to store</option><option value="damage">Mark damaged</option></select></div>
            <div><Label htmlFor="production-replacement-id">Replacement installation ID</Label><Input id="production-replacement-id" value={actionForm.replacement_for_id} onChange={(event) => setActionForm({ ...actionForm, replacement_for_id: event.target.value })} placeholder="Only for replace" /></div>
            <div className="md:col-span-2"><DialogFooter><Button disabled={busy} type="submit">Record action</Button></DialogFooter></div>
          </form>
        </DialogContent>
      </Dialog>}

      {can("drone.read") && <Card>
        <CardHeader><CardTitle>Installation history</CardTitle><CardDescription>Every component action is traceable. Production Managers approve install, remove, and replace actions before confirmation.</CardDescription></CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded-md border"><Table><TableHeader><TableRow><TableHead>Drone</TableHead><TableHead>Component</TableHead><TableHead>Action</TableHead><TableHead>Serial</TableHead><TableHead>Approval</TableHead><TableHead>Occurred</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader><TableBody>{installations.map((installation) => { const unit = unitById.get(installation.inventory_unit_id); return <TableRow key={installation.id}><TableCell>{installation.drone_serial_number ?? droneById.get(installation.drone_id)?.serial_number ?? "Drone serial pending"}</TableCell><TableCell>{installation.component_code ?? componentById.get(unit?.component_id ?? "")?.code ?? "Component code pending"}</TableCell><TableCell><Badge variant="outline">{installation.action}</Badge></TableCell><TableCell className="font-mono text-xs">{installation.component_serial_number ?? unit?.serial_number ?? "Serial pending"}</TableCell><TableCell>{installation.approved_by_membership_id ? <Badge>Approved</Badge> : <Badge variant="secondary">Pending</Badge>}</TableCell><TableCell>{new Date(installation.occurred_at).toLocaleString()}</TableCell><TableCell className="whitespace-nowrap text-right">{!installation.approved_by_membership_id && can("completion.confirm") && <Button className="whitespace-nowrap" type="button" size="sm" onClick={() => onReviewApproval(installation.id)}>Review approval</Button>}</TableCell></TableRow>; })}</TableBody></Table></div>
          {!installations.length && <p className="py-4 text-sm text-muted-foreground">No component actions have been recorded yet.</p>}
        </CardContent>
      </Card>}

      {can("drone.read") && <Card>
        <CardHeader><CardTitle>Production tasks</CardTitle><CardDescription>Assign and track work required to complete a drone.</CardDescription></CardHeader>
        <CardContent className="space-y-4">
          {can("assignment.manage") && (
            <Dialog>
              <DialogTrigger asChild><Button type="button" variant="outline">Add production task</Button></DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader><DialogTitle>Add production task</DialogTitle><DialogDescription>Assign work required to complete a drone.</DialogDescription></DialogHeader>
                <form className="grid gap-3 md:grid-cols-2" onSubmit={onCreateTask}>
                  <div><Label htmlFor="production-task-drone">Drone</Label><select id="production-task-drone" className={fieldClassName} required value={taskForm.drone_id} onChange={(event) => setTaskForm({ ...taskForm, drone_id: event.target.value })}><option value="">Select a drone</option>{drones.filter((drone) => drone.status !== "confirmed").map((drone) => <option key={drone.id} value={drone.id}>{drone.serial_number ?? "Drone serial pending"}</option>)}</select></div>
                  <div><Label htmlFor="production-task-title">Task</Label><Input id="production-task-title" required value={taskForm.title} onChange={(event) => setTaskForm({ ...taskForm, title: event.target.value })} placeholder="Install flight controller" /></div>
                  <div><Label htmlFor="production-task-assignee">Assign technician</Label><select id="production-task-assignee" className={fieldClassName} value={taskForm.assigned_to_membership_id} onChange={(event) => setTaskForm({ ...taskForm, assigned_to_membership_id: event.target.value })}><option value="">Unassigned</option>{assignees.map((assignee) => <option key={assignee.membership_id} value={assignee.membership_id}>{assignee.display_name}</option>)}</select></div>
                  <div><Label htmlFor="production-task-notes">Notes <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="production-task-notes" value={taskForm.notes} onChange={(event) => setTaskForm({ ...taskForm, notes: event.target.value })} placeholder="Instructions for the technician" /></div>
                  <div className="md:col-span-2"><DialogFooter><Button disabled={busy} type="submit">Add task</Button></DialogFooter></div>
                </form>
              </DialogContent>
            </Dialog>
          )}
          <div className="flex flex-wrap gap-2" aria-label="Production task status filter">
            {[{ value: "all", label: "All" }, { value: "open", label: "Open" }, { value: "in_progress", label: "In progress" }, { value: "completed", label: "Completed" }].map((filter) => <Button key={filter.value} type="button" size="sm" variant={taskFilter === filter.value ? "default" : "outline"} onClick={() => setTaskFilter(filter.value)}>{filter.label}</Button>)}
          </div>
          <div className="overflow-x-auto rounded-md border"><Table><TableHeader><TableRow><TableHead>Drone</TableHead><TableHead>Task</TableHead><TableHead>Assigned to</TableHead><TableHead>Status</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader><TableBody>{visibleTasks.map((task) => { const nextStatus = task.status === "open" ? "in_progress" : task.status === "in_progress" ? "completed" : null; const assignee = assignees.find((item) => item.membership_id === task.assigned_to_membership_id); return <TableRow key={task.id}><TableCell>{task.drone_serial_number ?? droneById.get(task.drone_id)?.serial_number ?? "Drone serial pending"}</TableCell><TableCell><div className="font-medium">{task.title}</div>{task.notes && <div className="text-xs text-muted-foreground">{task.notes}</div>}</TableCell><TableCell>{task.assignee_display_name ?? assignee?.display_name ?? (task.assigned_to_membership_id ? "Assigned technician" : "Unassigned")}</TableCell><TableCell><Badge variant={task.status === "completed" ? "default" : task.status === "cancelled" ? "destructive" : "secondary"}>{task.status.replace("_", " ")}</Badge></TableCell><TableCell className="whitespace-nowrap text-right">{nextStatus && (can("assignment.manage") || can("assignment.update_own")) && <Button className="whitespace-nowrap" type="button" size="sm" variant="outline" onClick={() => onUpdateTask(task, nextStatus)}>{nextStatus === "in_progress" ? "Start" : "Complete"}</Button>}</TableCell></TableRow>; })}</TableBody></Table></div>
          {!visibleTasks.length && <p className="text-sm text-muted-foreground">No production tasks match this filter.</p>}
        </CardContent>
      </Card>}

      {can("completion.confirm") && <Dialog open={confirmationDialogOpen} onOpenChange={setConfirmationDialogOpen}><DialogTrigger asChild><Button type="button" variant="outline" className="h-auto min-h-24 w-full justify-start text-left"><span><span className="block font-semibold">Confirm completed drone</span><span className="mt-1 block text-xs font-normal text-muted-foreground">Complete the production and quality checklist before locking the record.</span></span></Button></DialogTrigger><DialogContent className="max-w-3xl"><DialogHeader><DialogTitle>Confirm completed drone</DialogTitle><DialogDescription>All checklist items must be true. Confirmation locks normal edits and records the approving manager.</DialogDescription></DialogHeader><form className="space-y-4" onSubmit={onConfirmDrone}><select aria-label="Drone to confirm" className={fieldClassName} required value={confirmationDroneId} onChange={(event) => setConfirmationDroneId(event.target.value)}><option value="">Select a draft drone</option>{drones.filter((drone) => drone.status !== "confirmed").map((drone) => <option key={drone.id} value={drone.id}>{drone.serial_number ?? "Drone serial pending"}</option>)}</select><div className="grid gap-3 sm:grid-cols-2">{confirmationChecks.map((check: ConfirmationCheck) => <label className="flex items-center gap-2 rounded-md border p-3 text-sm" key={check.key}><input checked={checks[check.key] === true} onChange={(event) => setChecks({ ...checks, [check.key]: event.target.checked })} type="checkbox" />{check.label}</label>)}</div><DialogFooter><Button disabled={busy || !confirmationDroneId} type="submit">Confirm and lock drone</Button></DialogFooter></form></DialogContent></Dialog>}

      {can("completion.confirm") && drones.some((drone) => drone.status === "confirmed") && <Card><CardHeader><CardTitle>Reopen confirmed drone</CardTitle><CardDescription>Use only when a correction is required. The reason is mandatory and the action is recorded in the audit log.</CardDescription></CardHeader><CardContent className="flex flex-col gap-3 sm:flex-row sm:items-end"><div className="w-full sm:max-w-md"><Label htmlFor="production-reopen-drone">Confirmed drone</Label><select id="production-reopen-drone" className={fieldClassName} value={reopenDroneId} onChange={(event) => setReopenDroneId(event.target.value)}><option value="">Select a confirmed drone</option>{drones.filter((drone) => drone.status === "confirmed").map((drone) => <option key={drone.id} value={drone.id}>{drone.serial_number ?? "Drone serial pending"}</option>)}</select></div><Button type="button" variant="outline" disabled={!reopenDroneId} onClick={() => onOpenReopen(reopenDroneId)}>Reopen drone</Button></CardContent></Card>}

      <InstallationApprovalDialog open={Boolean(approvalInstallationId)} busy={busy} onOpenChange={onApprovalChange} onApprove={() => { if (approvalInstallationId) onApproveInstallation(approvalInstallationId); }} />
      <ReopenDroneDialog state={reopenState} busy={busy} onOpenChange={onReopenChange} onReasonChange={onReopenReasonChange} onSubmit={onSubmitReopen} />
    </div>
  );
}
