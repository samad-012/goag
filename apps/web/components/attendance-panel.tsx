"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { WORKSPACE_REFRESH_EVENT } from "@/lib/workspace-events";

type AttendanceRecord = {
  id: string;
  membership_id: string;
  member_display_name?: string | null;
  member_email?: string | null;
  work_date: string;
  status: string;
  late: boolean;
  check_in_at: string;
  check_out_at: string | null;
  check_in_distance_m: number;
  check_out_distance_m: number | null;
  correction_reason: string | null;
};

type LocationPayload = {
  device_id: string;
  latitude: number | null;
  longitude: number | null;
  accuracy_m: number | null;
  gps_denied: boolean;
};

type AttendanceMember = {
  membership_id: string;
  display_name: string;
  email: string;
};

type AttendanceException = {
  id: string;
  membership_id: string;
  work_date: string;
  reason: string;
  status: string;
  approved_by_membership_id: string;
  approved_at: string;
};

const deviceStorageKey = "goag.attendance.device_id";

async function attendanceRequest<T>(path: string, init?: RequestInit): Promise<T> {
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

function getDeviceId(): string {
  const existing = window.localStorage.getItem(deviceStorageKey);
  if (existing) return existing;
  const generated = typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `goag-${Date.now()}-${Math.random()}`;
  window.localStorage.setItem(deviceStorageKey, generated);
  return generated;
}

function getLocation(deviceId: string): Promise<LocationPayload> {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (payload: LocationPayload) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeout);
      resolve(payload);
    };
    const timeout = window.setTimeout(
      () => finish({ device_id: deviceId, latitude: null, longitude: null, accuracy_m: null, gps_denied: true }),
      12_000,
    );
    if (!navigator.geolocation) {
      finish({ device_id: deviceId, latitude: null, longitude: null, accuracy_m: null, gps_denied: true });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        finish({
          device_id: deviceId,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_m: position.coords.accuracy,
          gps_denied: false,
        }),
      () => finish({ device_id: deviceId, latitude: null, longitude: null, accuracy_m: null, gps_denied: true }),
      { enableHighAccuracy: true, maximumAge: 30_000, timeout: 10_000 },
    );
  });
}

function formatDateTime(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

function localDateTimeValue(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function AttendancePanel({ permissions }: { permissions: string[] }) {
  const canCheckIn = permissions.includes("attendance.check_in");
  const canReadAll = permissions.includes("attendance.read_all");
  const canCorrect = permissions.includes("attendance.correct");
  const canRead = true;
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [members, setMembers] = useState<AttendanceMember[]>([]);
  const [exceptions, setExceptions] = useState<AttendanceException[]>([]);
  const [registered, setRegistered] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [exceptionForm, setExceptionForm] = useState({ membership_id: "", work_date: "", reason: "" });
  const [correctionId, setCorrectionId] = useState<string | null>(null);
  const [correctionForm, setCorrectionForm] = useState({ check_in_at: "", check_out_at: "", reason: "" });

  const loadRecords = async () => {
    if (!canRead) return;
    setLoading(true);
    try {
      setRecords(await attendanceRequest<AttendanceRecord[]>(canReadAll ? "/attendance" : "/attendance/me"));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load attendance.");
    } finally {
      setLoading(false);
    }
  };

  const loadManagerData = async () => {
    if (!canReadAll) return;
    try {
      const [memberRows, exceptionRows] = await Promise.all([
        attendanceRequest<AttendanceMember[]>("/attendance/members"),
        attendanceRequest<AttendanceException[]>("/attendance/exceptions"),
      ]);
      setMembers(memberRows);
      setExceptions(exceptionRows);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load attendance management data.");
    }
  };

  useEffect(() => {
    void loadRecords();
    void loadManagerData();
    setExceptionForm((current) => ({ ...current, work_date: new Date().toISOString().slice(0, 10) }));
    const refresh = () => {
      void loadRecords();
      void loadManagerData();
    };
    window.addEventListener(WORKSPACE_REFRESH_EVENT, refresh);
    return () => window.removeEventListener(WORKSPACE_REFRESH_EVENT, refresh);
    // Permissions are fixed for the authenticated dashboard session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!canRead) return null;

  const run = async (operation: () => Promise<void>, successMessage: string) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await operation();
      await loadRecords();
      await loadManagerData();
      setMessage(successMessage);
    } catch (operationError) {
      setError(operationError instanceof Error ? operationError.message : "Attendance operation failed.");
    } finally {
      setBusy(false);
    }
  };

  const registerDevice = () =>
    run(async () => {
      await attendanceRequest("/me/device", { method: "POST", body: JSON.stringify({ device_id: getDeviceId() }) });
      setRegistered(true);
    }, "This browser is now registered as your only GOAG attendance device.");

  const recordAttendance = (action: "check-in" | "check-out") =>
    run(async () => {
      const payload = await getLocation(getDeviceId());
      await attendanceRequest(`/attendance/${action}`, { method: "POST", body: JSON.stringify(payload) });
    }, action === "check-in" ? "Attendance checked in." : "Attendance checked out.");

  const approveException = () =>
    run(async () => {
      await attendanceRequest("/attendance/exceptions", {
        method: "POST",
        body: JSON.stringify(exceptionForm),
      });
      setExceptionForm((current) => ({ ...current, membership_id: "", reason: "" }));
    }, "Off-site attendance exception approved.");

  const correctAttendance = () =>
    run(async () => {
      if (!correctionId) return;
      await attendanceRequest(`/attendance/${correctionId}/correct`, {
        method: "POST",
        body: JSON.stringify({
          check_in_at: correctionForm.check_in_at ? new Date(correctionForm.check_in_at).toISOString() : null,
          check_out_at: correctionForm.check_out_at ? new Date(correctionForm.check_out_at).toISOString() : null,
          reason: correctionForm.reason,
        }),
      });
      setCorrectionId(null);
      setCorrectionForm({ check_in_at: "", check_out_at: "", reason: "" });
    }, "Attendance correction saved and audited.");

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle>Attendance</CardTitle>
            <CardDescription>Check in and out from one registered device while inside the approved GOAG geofence.</CardDescription>
          </div>
          <Badge variant="outline">GPS + geofence</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        {canCheckIn && (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/30 p-3">
            <Button variant="outline" onClick={registerDevice} disabled={busy}>
              {registered ? "Device registered" : "Register this device"}
            </Button>
            <Button onClick={() => recordAttendance("check-in")} disabled={busy || !registered}>
              Check in
            </Button>
            <Button variant="secondary" onClick={() => recordAttendance("check-out")} disabled={busy || !registered}>
              Check out
            </Button>
            <span className="text-xs text-muted-foreground">GPS denied or poor accuracy will be rejected.</span>
          </div>
        )}
        {message && <p className="text-sm text-emerald-700">{message}</p>}
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <div>
          <h3 className="mb-2 text-sm font-medium">{canReadAll ? "Attendance history" : "My attendance history"}</h3>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading attendance…</p>
          ) : records.length === 0 ? (
            <p className="text-sm text-muted-foreground">No attendance records yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  {canReadAll && <TableHead>Employee</TableHead>}
                  <TableHead>Date</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Check in</TableHead>
                    <TableHead>Check out</TableHead>
                    <TableHead>Geofence</TableHead>
                    {canCorrect && <TableHead>Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((record) => (
                  <TableRow key={record.id}>
                    {canReadAll && <TableCell><div className="font-medium">{record.member_display_name ?? "Team member"}</div>{record.member_email && <div className="text-xs text-muted-foreground">{record.member_email}</div>}</TableCell>}
                    <TableCell>{record.work_date}</TableCell>
                    <TableCell>
                      <Badge variant={record.late ? "destructive" : "secondary"}>{record.late ? "Late" : "Present"}</Badge>
                    </TableCell>
                    <TableCell>{formatDateTime(record.check_in_at)}</TableCell>
                    <TableCell>{formatDateTime(record.check_out_at)}</TableCell>
                    <TableCell>{Math.round(record.check_in_distance_m)} m</TableCell>
                    {canCorrect && (
                      <TableCell>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setCorrectionId(record.id);
                            setCorrectionForm({
                              check_in_at: localDateTimeValue(record.check_in_at),
                              check_out_at: localDateTimeValue(record.check_out_at),
                              reason: "",
                            });
                          }}
                        >
                          Correct
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {canCorrect && canReadAll && (
          <div className="space-y-4 rounded-lg border bg-muted/20 p-4">
            <div>
              <h3 className="text-sm font-medium">Approve off-site attendance</h3>
              <p className="text-xs text-muted-foreground">GPS is still required. This approval allows the selected employee to attend outside the geofence for one date.</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <select
                className="h-9 rounded-md border border-input bg-background px-3 text-sm"
                value={exceptionForm.membership_id}
                onChange={(event) => setExceptionForm({ ...exceptionForm, membership_id: event.target.value })}
              >
                <option value="">Select employee</option>
                {members.map((member) => (
                  <option key={member.membership_id} value={member.membership_id}>
                    {member.display_name} · {member.email}
                  </option>
                ))}
              </select>
              <Input
                type="date"
                value={exceptionForm.work_date}
                onChange={(event) => setExceptionForm({ ...exceptionForm, work_date: event.target.value })}
              />
              <Input
                placeholder="Reason for off-site work"
                value={exceptionForm.reason}
                onChange={(event) => setExceptionForm({ ...exceptionForm, reason: event.target.value })}
              />
            </div>
            <Button onClick={approveException} disabled={busy || !exceptionForm.membership_id || !exceptionForm.work_date || !exceptionForm.reason.trim()}>
              Approve exception
            </Button>
            {exceptions.length > 0 && (
              <div className="text-xs text-muted-foreground">
                Approved exceptions: {exceptions.map((item) => `${item.work_date} (${item.reason})`).join(" · ")}
              </div>
            )}
          </div>
        )}

        {canCorrect && correctionId && (
          <div className="space-y-4 rounded-lg border bg-muted/20 p-4">
            <div>
              <h3 className="text-sm font-medium">Correct attendance</h3>
              <p className="text-xs text-muted-foreground">A reason is required. The original and corrected values are written to the audit log.</p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Input type="datetime-local" value={correctionForm.check_in_at} onChange={(event) => setCorrectionForm({ ...correctionForm, check_in_at: event.target.value })} />
              <Input type="datetime-local" value={correctionForm.check_out_at} onChange={(event) => setCorrectionForm({ ...correctionForm, check_out_at: event.target.value })} />
              <Input className="md:col-span-2" placeholder="Correction reason" value={correctionForm.reason} onChange={(event) => setCorrectionForm({ ...correctionForm, reason: event.target.value })} />
            </div>
            <div className="flex gap-2">
              <Button onClick={correctAttendance} disabled={busy || !correctionForm.reason.trim()}>Save correction</Button>
              <Button variant="ghost" onClick={() => setCorrectionId(null)}>Cancel</Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
