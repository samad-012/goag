"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";
import type { CurrentUserResponse } from "@/lib/api-client";
import { roleLabel } from "@/lib/workspace-config";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ActivityList } from "@/components/activity-list";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { LoadingSkeleton } from "@/components/loading-skeleton";
import { MetricCard } from "@/components/metric-card";
import { NeedsAttentionList, type AttentionItem } from "@/components/needs-attention-list";
import { QuickActions } from "@/components/quick-actions";
import { WORKSPACE_REFRESH_EVENT } from "@/lib/workspace-events";

export type DashboardAuditEvent = {
  action: string;
  entity_type: string;
  entity_id: string;
  action_label?: string;
  subject?: string | null;
  status_label?: string;
  created_at: string;
};

type DashboardSummary = {
  inventory_in_stock: number | null;
  inventory_issued: number | null;
  pending_component_requests: number | null;
  backordered_quantity: number | null;
  drones_in_production: number | null;
  confirmed_drones: number | null;
  open_production_tasks: number | null;
  my_attendance_days_last_30: number;
  company_attendance_days_last_30?: number | null;
  my_attendance_today_status: string | null;
  recent_audit_events: DashboardAuditEvent[];
};

type MetricDefinition = { key: keyof DashboardSummary; label: string; context: string; href: string };

const roleMetricMap: Record<string, MetricDefinition[]> = {
  MANAGING_DIRECTOR: [
    { key: "inventory_in_stock", label: "Stock on hand", context: "Open inventory", href: "/dashboard/inventory" },
    { key: "drones_in_production", label: "Drones in production", context: "Open production", href: "/dashboard/production" },
    { key: "pending_component_requests", label: "Pending requests", context: "Review requests", href: "/dashboard/inventory" },
    { key: "open_production_tasks", label: "Open tasks", context: "Review work", href: "/dashboard/production" },
    { key: "company_attendance_days_last_30", label: "Attendance records", context: "View attendance", href: "/dashboard/attendance" },
  ],
  PRODUCTION_MANAGER: [
    { key: "drones_in_production", label: "Active drones", context: "Open production", href: "/dashboard/production" },
    { key: "open_production_tasks", label: "Open tasks", context: "Review tasks", href: "/dashboard/production" },
    { key: "pending_component_requests", label: "Component requests", context: "Review issues", href: "/dashboard/production" },
    { key: "confirmed_drones", label: "Confirmed drones", context: "View history", href: "/dashboard/production" },
  ],
  STORE_MANAGER: [
    { key: "inventory_in_stock", label: "Stock on hand", context: "Open inventory", href: "/dashboard/inventory" },
    { key: "pending_component_requests", label: "Requests to review", context: "Review requests", href: "/dashboard/inventory" },
    { key: "backordered_quantity", label: "Backordered units", context: "Review shortages", href: "/dashboard/inventory" },
    { key: "inventory_issued", label: "Issued or installed", context: "View movement", href: "/dashboard/inventory" },
  ],
  TECHNICIAN: [
    { key: "open_production_tasks", label: "My open tasks", context: "Open my work", href: "/dashboard/production" },
    { key: "pending_component_requests", label: "My requests", context: "View requests", href: "/dashboard/inventory" },
    { key: "inventory_issued", label: "Issued or installed", context: "View component status", href: "/dashboard/inventory" },
    { key: "my_attendance_days_last_30", label: "Attendance days", context: "View attendance", href: "/dashboard/attendance" },
  ],
};

const roleSubtitles: Record<string, string> = {
  MANAGING_DIRECTOR: "Company-wide visibility across people, inventory, and production.",
  PRODUCTION_MANAGER: "Keep active drones, tasks, and completion decisions moving.",
  STORE_MANAGER: "Keep stock accurate and component handovers ready for production.",
  SALES_MANAGER: "Your sales workspace is being prepared for customer and delivery operations.",
  TECHNICIAN: "Start with your assigned work, requests, and components.",
  AFTER_SALES_MANAGER: "This role is reserved for a future after-sales workspace.",
};

const DASHBOARD_REQUEST_TIMEOUT_MS = 8_000;

async function dashboardRequest<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), DASHBOARD_REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(`/api/backend${path}`, { cache: "no-store", signal: controller.signal });
  } catch (requestError) {
    if (requestError instanceof DOMException && requestError.name === "AbortError") {
      throw new Error("The operational overview took too long to respond. Check that the API is running, then retry.");
    }
    throw new Error("The operational overview could not be reached. Check that the API is running, then retry.");
  } finally {
    window.clearTimeout(timeoutId);
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

function createAttentionItems(summary: DashboardSummary, roleCode: string): AttentionItem[] {
  const items: AttentionItem[] = [];
  if ((summary.backordered_quantity ?? 0) > 0) {
    items.push({ label: "Components are backordered", detail: `${summary.backordered_quantity} unit(s) still need fulfilment.`, href: "/dashboard/inventory", severity: "blocked" });
  }
  if ((summary.pending_component_requests ?? 0) > 0) {
    items.push({ label: roleCode === "TECHNICIAN" ? "Your component requests are pending" : "Component requests need review", detail: `${summary.pending_component_requests} request(s) are waiting for action.`, href: "/dashboard/inventory", severity: "attention" });
  }
  if ((summary.open_production_tasks ?? 0) > 0) {
    items.push({ label: roleCode === "TECHNICIAN" ? "Your production work is open" : "Production tasks are open", detail: `${summary.open_production_tasks} task(s) need progress or completion.`, href: "/dashboard/production", severity: "attention" });
  }
  if (!summary.my_attendance_today_status) {
    items.push({ label: "Attendance is not recorded today", detail: "Check in from your registered device when you arrive at GOAG.", href: "/dashboard/attendance", severity: "info" });
  }
  return items.slice(0, 5);
}

function salesPreview() {
  return (
    <section id="sales-preview" aria-label="Sales workspace">
      <EmptyState
        title="Sales workspace coming next"
        description="Customers, quotations, orders, deliveries, and sold-drone records are planned for the Sales workspace. The supporting API module is not implemented yet."
        action={<Button asChild variant="outline"><Link href="/dashboard/attendance">View my attendance <ArrowRight aria-hidden="true" /></Link></Button>}
      />
    </section>
  );
}

export function RoleOverview({ currentUser }: { currentUser: CurrentUserResponse }) {
  const roleCode = currentUser.role_codes[0] ?? "";
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSummary() {
    setLoading(true);
    setError("");
    try {
      setSummary(await dashboardRequest<DashboardSummary>("/dashboard/summary"));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load your operational overview.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSummary();
    const refresh = () => void loadSummary();
    window.addEventListener(WORKSPACE_REFRESH_EVENT, refresh);
    return () => window.removeEventListener(WORKSPACE_REFRESH_EVENT, refresh);
  }, []);

  if (roleCode === "AFTER_SALES_MANAGER") {
    return (
      <section aria-label="After-sales overview" className="space-y-4">
        <EmptyState
          title="After-sales workspace is not enabled yet"
          description="This role is reserved for a future after-sales module. Your personal attendance remains available below."
          action={<Button asChild variant="outline"><Link href="/dashboard/attendance">View my attendance <ArrowRight aria-hidden="true" /></Link></Button>}
        />
      </section>
    );
  }

  if (roleCode === "SALES_MANAGER") {
    return salesPreview();
  }

  const metricDefinitions = roleMetricMap[roleCode] ?? roleMetricMap.MANAGING_DIRECTOR;
  const metrics = summary
    ? metricDefinitions.filter((definition) => typeof summary[definition.key] === "number").slice(0, 6)
    : [];
  const attentionItems = summary ? createAttentionItems(summary, roleCode) : [];
  const quickActions = roleCode === "STORE_MANAGER"
    ? [{ label: "Open inventory", href: "/dashboard/inventory" }, { label: "Review requests", href: "/dashboard/inventory" }, { label: "Open mailbox", href: "/dashboard/mailbox" }]
    : roleCode === "PRODUCTION_MANAGER"
      ? [{ label: "Open production", href: "/dashboard/production" }, { label: "Review tasks", href: "/dashboard/production" }, { label: "Confirm a drone", href: "/dashboard/production" }]
      : roleCode === "TECHNICIAN"
        ? [{ label: "Open my work", href: "/dashboard/production" }, { label: "View attendance", href: "/dashboard/attendance" }]
        : [{ label: "Review operations", href: "/dashboard/inventory" }, { label: "View attendance", href: "/dashboard/attendance" }, { label: "Open mailbox", href: "/dashboard/mailbox" }];

  return (
    <section aria-label="Role overview" className="space-y-5">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-primary">{roleLabel(roleCode)}</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight">Today&apos;s overview</h2>
          <p className="mt-1 text-sm text-muted-foreground">{roleSubtitles[roleCode] ?? roleSubtitles.MANAGING_DIRECTOR}</p>
        </div>
        <Button onClick={() => void loadSummary()} variant="outline" disabled={loading}>
          <RefreshCw aria-hidden="true" className={loading ? "animate-spin" : undefined} />
          {loading ? "Refreshing…" : "Refresh overview"}
        </Button>
      </div>

      {loading && !summary ? <LoadingSkeleton /> : null}

      {error && summary ? <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive" role="alert">{error}</div> : null}
      {!loading && error && !summary ? (
        <ErrorState
          description={error}
          onRetry={() => void loadSummary()}
          secondaryHref="/dashboard/attendance"
          secondaryLabel="Open attendance"
        />
      ) : null}

      {summary ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {metrics.map((definition) => (
              <MetricCard context={definition.context} href={definition.href} key={definition.key} label={definition.label} value={summary[definition.key] as number} />
            ))}
          </div>
          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <NeedsAttentionList items={attentionItems.length ? attentionItems : [{ label: "Operations are clear", detail: "No urgent items are waiting for your attention.", href: "/dashboard", severity: "clear" }]} />
            <ActivityList events={summary.recent_audit_events} />
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
              <CardDescription>Jump directly to the work most relevant to your role.</CardDescription>
            </CardHeader>
            <CardContent><QuickActions actions={quickActions} /></CardContent>
          </Card>
        </>
      ) : null}
    </section>
  );
}
