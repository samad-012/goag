"use client";

import { useEffect, useState } from "react";
import { RotateCcw, UserPlus, UsersRound } from "lucide-react";
import { roleLabel } from "@/lib/workspace-config";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { WORKSPACE_REFRESH_EVENT } from "@/lib/workspace-events";

type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  status: string;
  role_codes: string[];
  membership_status: string;
};

const roleOptions = [
  "MANAGING_DIRECTOR",
  "PRODUCTION_MANAGER",
  "STORE_MANAGER",
  "SALES_MANAGER",
  "TECHNICIAN",
  "AFTER_SALES_MANAGER",
];

async function teamRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function TeamAdminPanel({ permissions }: { permissions: string[] }) {
  const canRead = permissions.includes("members.read");
  const canManage = permissions.includes("members.manage");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", display_name: "", role_code: "TECHNICIAN" });

  const loadUsers = async () => {
    if (!canRead) return;
    setLoading(true);
    setError("");
    try {
      setUsers(await teamRequest<AdminUser[]>("/admin/users"));
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load team members.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
    const refresh = () => void loadUsers();
    window.addEventListener(WORKSPACE_REFRESH_EVENT, refresh);
    return () => window.removeEventListener(WORKSPACE_REFRESH_EVENT, refresh);
  }, [canRead]);

  const createUser = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await teamRequest<AdminUser>("/admin/users", {
        method: "POST",
        body: JSON.stringify({ email: form.email, display_name: form.display_name, role_codes: [form.role_code] }),
      });
      setForm({ email: "", display_name: "", role_code: "TECHNICIAN" });
      setOpen(false);
      setMessage("User invited. They can be linked when they sign in with the same verified email.");
      await loadUsers();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to create the user.");
    } finally {
      setBusy(false);
    }
  };

  const resetDevice = async (user: AdminUser) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await teamRequest<void>(`/admin/users/${user.id}/device/reset`, { method: "POST" });
      setMessage(`Registered device reset for ${user.display_name}.`);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Unable to reset the registered device.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      {(error || message) && <div className={`rounded-xl border p-4 text-sm ${error ? "border-destructive/30 bg-destructive/5 text-destructive" : "border-emerald-500/30 bg-emerald-500/5 text-emerald-800"}`} role={error ? "alert" : "status"}>{error || message}</div>}
      <Card>
        <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2"><UsersRound aria-hidden="true" className="size-5 text-primary" /> GOAG team members</CardTitle>
            <CardDescription className="mt-1">Review membership status and assigned access. Passwords are managed by Supabase Auth.</CardDescription>
          </div>
          {canManage && <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild><Button><UserPlus aria-hidden="true" /> Invite user</Button></DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader><DialogTitle>Invite a GOAG user</DialogTitle><DialogDescription>Create the application membership first. The user must later sign in through Supabase Auth using this same email address.</DialogDescription></DialogHeader>
              <form className="space-y-4" onSubmit={createUser}>
                <div className="space-y-2"><Label htmlFor="team-user-name">Display name</Label><Input id="team-user-name" required value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} placeholder="Amina Khan" /></div>
                <div className="space-y-2"><Label htmlFor="team-user-email">Email address</Label><Input id="team-user-email" required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="name@goag.example" /></div>
                <div className="space-y-2"><Label htmlFor="team-user-role">Role</Label><select id="team-user-role" className="flex h-9 w-full rounded-lg border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring" value={form.role_code} onChange={(event) => setForm({ ...form, role_code: event.target.value })}>{roleOptions.map((role) => <option key={role} value={role}>{roleLabel(role)}</option>)}</select></div>
                <DialogFooter><Button disabled={busy} type="submit">{busy ? "Creating…" : "Create user"}</Button></DialogFooter>
              </form>
            </DialogContent>
          </Dialog>}
        </CardHeader>
        <CardContent>
          {loading ? <p className="py-6 text-sm text-muted-foreground">Loading team members…</p> : users.length ? <div className="overflow-x-auto rounded-md border"><Table><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Email</TableHead><TableHead>Role</TableHead><TableHead>Status</TableHead>{canManage && <TableHead className="text-right">Actions</TableHead>}</TableRow></TableHeader><TableBody>{users.map((user) => <TableRow key={user.id}><TableCell className="font-medium">{user.display_name}</TableCell><TableCell>{user.email}</TableCell><TableCell><div className="flex flex-wrap gap-1">{user.role_codes.map((role) => <Badge key={role} variant="outline">{roleLabel(role)}</Badge>)}</div></TableCell><TableCell><Badge variant={user.status === "active" && user.membership_status === "active" ? "default" : "secondary"}>{user.status === "active" ? user.membership_status : user.status}</Badge></TableCell>{canManage && <TableCell className="text-right"><Button className="whitespace-nowrap" disabled={busy} onClick={() => resetDevice(user)} size="sm" type="button" variant="outline"><RotateCcw aria-hidden="true" /> Reset device</Button></TableCell>}</TableRow>)}</TableBody></Table></div> : <p className="py-6 text-sm text-muted-foreground">No users have been added yet.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
