"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type AuditEvent = {
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
  company_attendance_days_last_30: number | null;
  my_attendance_today_status: string | null;
  recent_audit_events: AuditEvent[];
};

async function dashboardRequest<T>(path: string): Promise<T> {
  const response = await fetch(`/api/backend${path}`, { cache: "no-store" });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export function OperationalDashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadSummary() {
    setLoading(true);
    setError("");
    try {
      setSummary(await dashboardRequest<DashboardSummary>("/dashboard/summary"));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load operational dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSummary();
  }, []);

  const metrics = summary
    ? [
        ["In stock", summary.inventory_in_stock],
        ["Issued or installed", summary.inventory_issued],
        ["Pending requests", summary.pending_component_requests],
        ["Backordered quantity", summary.backordered_quantity],
        ["Drones in production", summary.drones_in_production],
        ["Confirmed drones", summary.confirmed_drones],
        ["Open production tasks", summary.open_production_tasks],
        ["My attendance days (30d)", summary.my_attendance_days_last_30],
        ["Attendance records (30d)", summary.company_attendance_days_last_30],
      ].filter(([, value]) => value !== null && value !== undefined)
    : [];

  return (
    <section className="space-y-4" aria-label="Operational dashboard">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Live operational view</p>
          <h2 className="text-2xl font-semibold tracking-tight">Operational dashboard</h2>
          <p className="text-sm text-muted-foreground">Read-only metrics are filtered by your GOAG permissions.</p>
        </div>
        <Button type="button" variant="outline" onClick={() => void loadSummary()} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh dashboard"}
        </Button>
      </div>

      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
      {loading && !summary ? <p className="text-sm text-muted-foreground">Loading operational metrics…</p> : null}

      {summary ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {metrics.map(([label, value]) => (
              <Card key={label} size="sm">
                <CardHeader>
                  <CardDescription>{label}</CardDescription>
                  <CardTitle className="text-2xl">{value}</CardTitle>
                </CardHeader>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>My attendance</CardTitle>
                <CardDescription>Your attendance is visible to you regardless of management permissions.</CardDescription>
              </CardHeader>
              <CardContent>
                <Badge variant={summary.my_attendance_today_status ? "secondary" : "outline"}>
                  Today: {summary.my_attendance_today_status ?? "Not recorded"}
                </Badge>
              </CardContent>
            </Card>

            {summary.recent_audit_events.length > 0 ? (
              <Card>
                <CardHeader>
                  <CardTitle>Recent audit activity</CardTitle>
                  <CardDescription>Visible to Managing Directors for operational oversight.</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Action</TableHead>
                        <TableHead>Entity</TableHead>
                        <TableHead>Time</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.recent_audit_events.map((event, index) => (
                        <TableRow key={`${event.entity_id}-${index}`}>
                          <TableCell className="font-medium">{event.action_label ?? event.action}</TableCell>
                          <TableCell>{event.subject ?? event.entity_type}</TableCell>
                          <TableCell className="text-muted-foreground">{formatDate(event.created_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  );
}
