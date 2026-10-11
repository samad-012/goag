"use client";

import { Dispatch, FormEvent, SetStateAction } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ComponentCatalogTable } from "@/components/component-catalog-table";
import { OpeningInventoryTable } from "@/components/opening-inventory-table";
import { RequestReviewDialog, type ReviewState } from "@/components/workflow-review-dialogs";
import type { Component, ComponentRequest, Drone, InventoryUnit, IssueForm, ProductionTask, RequestForm, RequestItem } from "@/components/workflow-types";

const fieldClassName = "h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring";
const createNewValue = "__new__";

type InventoryModuleProps = {
  roleCodes: string[];
  components: Component[];
  units: InventoryUnit[];
  drones: Drone[];
  requests: ComponentRequest[];
  tasks: ProductionTask[];
  componentById: Map<string, Component>;
  droneById: Map<string, Drone>;
  openRequestItems: Array<{ request: ComponentRequest; item: RequestItem }>;
  busy: boolean;
  can: (permission: string) => boolean;
  requestForm: RequestForm;
  setRequestForm: Dispatch<SetStateAction<RequestForm>>;
  issueForm: IssueForm;
  setIssueForm: Dispatch<SetStateAction<IssueForm>>;
  issueDialogOpen: boolean;
  setIssueDialogOpen: (open: boolean) => void;
  serialDraft: Record<string, string>;
  setSerialDraft: Dispatch<SetStateAction<Record<string, string>>>;
  reviewState: ReviewState;
  reviewReason: string;
  setReviewReason: (reason: string) => void;
  onOpeningInventorySaved: () => void;
  onCreateRequest: (event: FormEvent) => void;
  onIssueComponents: (event: FormEvent) => void;
  onAssignSerial: (unit: InventoryUnit) => void;
  onPrepareIssue: (request: ComponentRequest) => void;
  onRejectRequest: (requestId: string) => void;
  onCancelRequest: (requestId: string) => void;
  onReviewChange: (open: boolean) => void;
  onSubmitReview: (event: FormEvent) => void;
};

export function InventoryModule({
  roleCodes,
  components,
  units,
  drones,
  requests,
  tasks,
  componentById,
  droneById,
  openRequestItems,
  busy,
  can,
  requestForm,
  setRequestForm,
  issueForm,
  setIssueForm,
  issueDialogOpen,
  setIssueDialogOpen,
  serialDraft,
  setSerialDraft,
  reviewState,
  reviewReason,
  setReviewReason,
  onOpeningInventorySaved,
  onCreateRequest,
  onIssueComponents,
  onAssignSerial,
  onPrepareIssue,
  onRejectRequest,
  onCancelRequest,
  onReviewChange,
  onSubmitReview,
}: InventoryModuleProps) {
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestFilter = searchParams.get("request_status") ?? "all";
  const isStoreManager = roleCodes.includes("STORE_MANAGER");
  const isProductionManager = roleCodes.includes("PRODUCTION_MANAGER");
  const isTechnician = roleCodes.includes("TECHNICIAN");
  const focus = isStoreManager
    ? { title: "Store control", description: "Receive serialized stock, review requests, issue available quantities, and record substitutions." }
    : isTechnician
      ? { title: "Component handover", description: "Request the parts needed for your assigned work and record serial numbers when they are issued." }
      : isProductionManager
        ? { title: "Production support", description: "Check component availability and request the serialized parts needed to keep drone assembly moving." }
      : { title: "Director oversight", description: "Review serialized stock, request queues, and traceability across GOAG operations." };
  const inStockCount = units.filter((unit) => unit.status === "in_stock").length;
  const missingSerialCount = units.filter((unit) => !unit.serial_number && unit.status !== "in_stock").length;
  const pendingRequestCount = requests.filter((request) => ["pending", "partially_issued"].includes(request.status)).length;
  const damagedCount = units.filter((unit) => unit.status === "damaged").length;
  const visibleRequests = requests.filter((request) => {
    if (requestFilter === "needs_action") return ["pending", "partially_issued"].includes(request.status);
    if (requestFilter === "fulfilled") return request.status === "fulfilled";
    if (requestFilter === "cancelled") return ["cancelled", "rejected", "partially_rejected"].includes(request.status);
    return true;
  });
  const setRequestFilter = (value: string) => {
    const next = new URLSearchParams(searchParams.toString());
    if (value === "all") next.delete("request_status");
    else next.set("request_status", value);
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };
  return (
    <div className="space-y-6" aria-label="Inventory workspace">
      <Card className="border-primary/15 bg-primary/[0.03]" size="sm">
        <CardContent className="flex flex-col gap-1 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="text-sm font-semibold">{focus.title}</p><p className="text-xs text-muted-foreground">{focus.description}</p></div>
          <Badge className="w-fit" variant="outline">Role-filtered workspace</Badge>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Inventory status summary">
        {[
          ["In stock", inStockCount, "Available serialized units"],
          ["Requests needing action", pendingRequestCount, "Pending or partially issued"],
          ["Missing serials", missingSerialCount, "Issued units awaiting serials"],
          ["Damaged", damagedCount, "Units needing review"],
        ].map(([label, value, detail]) => (
          <Card key={label} size="sm"><CardContent className="py-4"><p className="text-xs font-medium text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-semibold">{value}</p><p className="text-xs text-muted-foreground">{detail}</p></CardContent></Card>
        ))}
      </div>

      {can("inventory.receive") && <OpeningInventoryTable components={components} onSaved={onOpeningInventorySaved} />}
      {can("inventory.read") && <ComponentCatalogTable components={components} units={units} />}

      {can("request.create") && <Dialog>
        <DialogTrigger asChild><Button type="button" variant="outline" className="h-auto min-h-24 w-full justify-start text-left"><span><span className="block font-semibold">Request components</span><span className="mt-1 block text-xs font-normal text-muted-foreground">Submit a component request for an active drone.</span></span></Button></DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>Request components</DialogTitle><DialogDescription>Technicians and production can request parts for a drone.</DialogDescription></DialogHeader>
          <form className="space-y-3" onSubmit={onCreateRequest}>
            <div><Label htmlFor="inventory-request-drone">Drone</Label><select id="inventory-request-drone" className={fieldClassName} required value={requestForm.drone_id} onChange={(event) => setRequestForm({ ...requestForm, drone_id: event.target.value })}><option value="">Select a drone</option>{drones.filter((drone) => drone.status !== "confirmed").map((drone) => <option key={drone.id} value={drone.id}>{drone.serial_number ?? "Drone serial pending"}</option>)}</select></div>
            <div><Label htmlFor="inventory-request-component">Component</Label><select id="inventory-request-component" className={fieldClassName} required value={requestForm.component_id} onChange={(event) => setRequestForm({ ...requestForm, component_id: event.target.value })}><option value="">Select a component</option>{components.map((component) => <option key={component.id} value={component.id}>{component.code} · {component.name}</option>)}<option value={createNewValue}>Component not listed — add to catalog</option></select></div>
            {requestForm.component_id === createNewValue && <div className="grid gap-3 rounded-md border bg-muted/30 p-3 sm:grid-cols-2"><div><Label htmlFor="inventory-new-component-name">New component name</Label><Input id="inventory-new-component-name" required value={requestForm.new_component_name} onChange={(event) => setRequestForm({ ...requestForm, new_component_name: event.target.value })} placeholder="Flight controller" /></div><div><Label htmlFor="inventory-new-component-code">Component code <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="inventory-new-component-code" value={requestForm.new_component_code} onChange={(event) => setRequestForm({ ...requestForm, new_component_code: event.target.value })} placeholder="Auto-generated from name" /></div><div className="sm:col-span-2"><Label htmlFor="inventory-new-component-category">Category</Label><Input id="inventory-new-component-category" required value={requestForm.new_component_category} onChange={(event) => setRequestForm({ ...requestForm, new_component_category: event.target.value })} placeholder="Electronics" /></div></div>}
            <div><Label htmlFor="inventory-request-quantity">Quantity</Label><Input id="inventory-request-quantity" min="1" type="number" required value={requestForm.quantity} onChange={(event) => setRequestForm({ ...requestForm, quantity: event.target.value })} /></div>
            <DialogFooter><Button disabled={busy} type="submit">Submit request</Button></DialogFooter>
          </form>
        </DialogContent>
      </Dialog>}

      {can("inventory.issue") && <div className="grid gap-4 xl:grid-cols-2">
        <Dialog open={issueDialogOpen} onOpenChange={setIssueDialogOpen}>
          <DialogTrigger asChild><Button type="button" variant="outline" className="h-auto min-h-24 justify-start text-left"><span><span className="block font-semibold">Issue components</span><span className="mt-1 block text-xs font-normal text-muted-foreground">Issue all or part of a request; the balance remains pending.</span></span></Button></DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader><DialogTitle>Issue components</DialogTitle><DialogDescription>Issue all or part of a request. The balance remains pending.</DialogDescription></DialogHeader>
            <form className="space-y-3" onSubmit={onIssueComponents}>
              <div><Label htmlFor="inventory-issue-item">Pending request item</Label><select id="inventory-issue-item" className={fieldClassName} required value={issueForm.request_item_id} onChange={(event) => setIssueForm({ ...issueForm, request_item_id: event.target.value })}><option value="">Select a pending item</option>{openRequestItems.map(({ request, item }) => <option key={item.id} value={`${request.id}|${item.id}`}>{request.drone_serial_number ?? droneById.get(request.drone_id)?.serial_number ?? "Drone serial pending"} · {item.component_code ?? componentById.get(item.component_id)?.code ?? "Component code pending"} · {item.pending_quantity} pending</option>)}</select></div>
              <div><Label htmlFor="inventory-issue-quantity">Issue quantity</Label><Input id="inventory-issue-quantity" min="1" type="number" required value={issueForm.quantity} onChange={(event) => setIssueForm({ ...issueForm, quantity: event.target.value })} /></div>
              <div><Label htmlFor="inventory-issue-serials">Serial number(s) at handover</Label><Input id="inventory-issue-serials" value={issueForm.serial_numbers} onChange={(event) => setIssueForm({ ...issueForm, serial_numbers: event.target.value })} placeholder="FC-0001, FC-0002" /><p className="mt-1 text-xs text-muted-foreground">Enter one serial per issued unit. Leave blank only when the serial is not yet available.</p></div>
              <div><Label htmlFor="inventory-substitute-component">Substitute component (optional)</Label><select id="inventory-substitute-component" className={fieldClassName} value={issueForm.substituted_component_id} onChange={(event) => setIssueForm({ ...issueForm, substituted_component_id: event.target.value })}><option value="">No substitution</option>{components.map((component) => <option key={component.id} value={component.id}>{component.code} · {component.name}</option>)}</select></div>
              <DialogFooter><Button disabled={busy || !openRequestItems.length} type="submit">Issue component quantity</Button></DialogFooter>
            </form>
          </DialogContent>
        </Dialog>

        <Dialog>
          <DialogTrigger asChild><Button type="button" variant="outline" className="h-auto min-h-24 justify-start text-left"><span><span className="block font-semibold">Assign component serials</span><span className="mt-1 block text-xs font-normal text-muted-foreground">Record missing serials before installation.</span></span></Button></DialogTrigger>
          <DialogContent className="max-w-3xl">
            <DialogHeader><DialogTitle>Assign component serials</DialogTitle><DialogDescription>Every physical unit needs a serial before installation.</DialogDescription></DialogHeader>
            <div className="space-y-3">{units.filter((unit) => !unit.serial_number && unit.status !== "in_stock").map((unit) => <div className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-end" key={unit.id}><div className="min-w-0 flex-1"><p className="text-sm font-medium">{componentById.get(unit.component_id)?.name ?? "Component unit"}</p><p className="text-xs text-muted-foreground">Serial number is pending</p></div><div className="flex gap-2"><Input aria-label="Component serial number" value={serialDraft[unit.id] ?? ""} onChange={(event) => setSerialDraft((current) => ({ ...current, [unit.id]: event.target.value }))} placeholder="FC-0001" /><Button type="button" disabled={busy || !serialDraft[unit.id]?.trim()} onClick={() => onAssignSerial(unit)}>Save serial</Button></div></div>)}{!units.some((unit) => !unit.serial_number && unit.status !== "in_stock") && <p className="text-sm text-muted-foreground">No issued components are waiting for serial numbers.</p>}</div>
          </DialogContent>
        </Dialog>
      </div>}

      {can("request.read_all") && <section className="space-y-3">
        <div><h3 className="text-lg font-semibold">Request review</h3><p className="text-sm text-muted-foreground">Review live requests, reject them with a reason, or prepare a pending request for issue.</p></div>
        <div className="flex flex-wrap gap-2" aria-label="Request status filter">
          {[{ value: "all", label: "All" }, { value: "needs_action", label: "Needs action" }, { value: "fulfilled", label: "Fulfilled" }, { value: "cancelled", label: "Rejected or cancelled" }].map((filter) => <Button key={filter.value} type="button" size="sm" variant={requestFilter === filter.value ? "default" : "outline"} onClick={() => setRequestFilter(filter.value)}>{filter.label}</Button>)}
        </div>
        <div className="overflow-x-auto rounded-md border">
          <Table><TableHeader><TableRow><TableHead>Drone</TableHead><TableHead>Status</TableHead><TableHead>Components</TableHead><TableHead>Created</TableHead><TableHead className="text-right">Actions</TableHead></TableRow></TableHeader><TableBody>
            {visibleRequests.map((request) => {
              const drone = droneById.get(request.drone_id);
              const hasPending = request.items.some((item) => item.pending_quantity > 0);
              const canReject = ["pending", "partially_issued"].includes(request.status);
              const droneTasks = tasks.filter((task) => task.drone_id === request.drone_id);
              const productionCompleted = droneTasks.length > 0 && droneTasks.every((task) => task.status === "completed");
              const canCancel = hasPending && (drone?.status === "confirmed" || productionCompleted) && !["rejected", "partially_rejected", "cancelled", "fulfilled"].includes(request.status);
              return <TableRow key={request.id}><TableCell className="font-medium">{request.drone_serial_number ?? drone?.serial_number ?? "Drone serial pending"}</TableCell><TableCell><Badge variant={request.status === "fulfilled" ? "default" : request.status.includes("reject") ? "destructive" : "secondary"}>{request.status}</Badge></TableCell><TableCell>{request.items.map((item) => `${item.component_code ?? componentById.get(item.component_id)?.code ?? "Component code pending"}: ${item.issued_quantity}/${item.requested_quantity} issued · ${item.pending_quantity} pending`).join(" · ")}</TableCell><TableCell>{new Date(request.created_at).toLocaleDateString()}</TableCell><TableCell><div className="flex flex-wrap justify-end gap-2">{hasPending && <Button className="whitespace-nowrap" type="button" size="sm" variant="outline" onClick={() => onPrepareIssue(request)}>Prepare issue</Button>}{canReject && <Button className="whitespace-nowrap" type="button" size="sm" variant="destructive" onClick={() => onRejectRequest(request.id)}>Reject</Button>}{canCancel && <Button className="whitespace-nowrap" type="button" size="sm" variant="outline" onClick={() => onCancelRequest(request.id)}>Cancel remaining</Button>}</div></TableCell></TableRow>;
            })}
          </TableBody></Table>
        </div>
        {!visibleRequests.length && <p className="text-sm text-muted-foreground">No requests match this filter.</p>}
      </section>}

      <RequestReviewDialog state={reviewState} reason={reviewReason} busy={busy} onOpenChange={onReviewChange} onReasonChange={setReviewReason} onSubmit={onSubmitReview} />
    </div>
  );
}
