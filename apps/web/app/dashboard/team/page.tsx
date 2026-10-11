import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { TeamAdminPanel } from "@/components/team-admin-panel";
import { getDashboardContext } from "@/lib/dashboard-context";

export default async function TeamPage() {
  const { currentUser, apiError } = await getDashboardContext();
  const canRead = currentUser?.permission_codes.includes("members.read") ?? false;
  return <AppShell activeKey="team" currentUser={currentUser}><div className="space-y-6"><header><p className="text-sm font-medium text-primary">Administration</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Team & access</h1><p className="mt-2 max-w-2xl text-muted-foreground">Manage GOAG users, memberships, and role access.</p></header>{!currentUser ? <AccessError message={apiError} /> : canRead ? <TeamAdminPanel permissions={currentUser.permission_codes} /> : <EmptyState title="Team administration unavailable" description="Your current role does not have access to team administration." />}</div></AppShell>;
}

function AccessError({ message }: { message: string }) { return <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm" role="alert">{message}</div>; }
