"use client";

import { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

const fieldClassName =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring";

export type ReviewState = { requestId: string; action: "reject" | "cancel" } | null;
export type ReopenState = { droneId: string; reason: string } | null;

export function RequestReviewDialog({
  state,
  reason,
  busy,
  onOpenChange,
  onReasonChange,
  onSubmit,
}: {
  state: ReviewState;
  reason: string;
  busy: boolean;
  onOpenChange: (open: boolean) => void;
  onReasonChange: (reason: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  const isCancel = state?.action === "cancel";
  return (
    <Dialog open={Boolean(state)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isCancel ? "Cancel remaining quantity" : "Reject component request"}</DialogTitle>
          <DialogDescription>
            {isCancel
              ? "Cancel the remaining quantity after production tasks are complete. The cancellation will be recorded in the audit history."
              : "Provide a reason before rejecting this request. If some quantity was already issued, the request will be marked partially rejected."}
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <Label htmlFor="review-reason">Reason</Label>
            <textarea
              id="review-reason"
              className={`${fieldClassName} min-h-24 py-2`}
              required
              value={reason}
              onChange={(event) => onReasonChange(event.target.value)}
              placeholder="Enter the reason"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
            <Button type="submit" variant={state?.action === "reject" ? "destructive" : "default"} disabled={busy || !reason.trim()}>
              {isCancel ? "Cancel quantity" : "Reject request"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function InstallationApprovalDialog({
  open,
  busy,
  onOpenChange,
  onApprove,
}: {
  open: boolean;
  busy: boolean;
  onOpenChange: (open: boolean) => void;
  onApprove: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Approve component action</DialogTitle>
          <DialogDescription>
            Confirm that this installation, removal, replacement, return, or damage action matches the physical component movement.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Keep pending</Button>
          <Button type="button" disabled={busy} onClick={onApprove}>Approve action</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ReopenDroneDialog({
  state,
  busy,
  onOpenChange,
  onReasonChange,
  onSubmit,
}: {
  state: ReopenState;
  busy: boolean;
  onOpenChange: (open: boolean) => void;
  onReasonChange: (reason: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <Dialog open={Boolean(state)} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reopen confirmed drone</DialogTitle>
          <DialogDescription>Reopening unlocks normal production edits. Explain what needs correction before continuing.</DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <Label htmlFor="reopen-reason">Reason</Label>
            <textarea
              id="reopen-reason"
              className={`${fieldClassName} min-h-24 py-2`}
              required
              value={state?.reason ?? ""}
              onChange={(event) => onReasonChange(event.target.value)}
              placeholder="Describe the correction required"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
            <Button type="submit" disabled={busy || !state?.reason.trim()}>Reopen drone</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
