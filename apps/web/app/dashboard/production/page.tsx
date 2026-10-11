import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { WorkflowPanel } from "@/components/workflow-panel";
import { Button } from "@/components/ui/button";
import { getDashboardContext } from "@/lib/dashboard-context";
import { hasAnyPermission } from "@/lib/workspace-config";

export default async function ProductionPage() {
  const { currentUser, apiError } = await getDashboardContext();
  const canRead = Boolean(currentUser && hasAnyPermission(currentUser.permission_codes, ["drone.read", "drone.create", "assignment.manage", "completion.confirm", "component.install"]));
  return <AppShell activeKey="production" currentUser={currentUser}><div className="space-y-6"><header><p className="text-sm font-medium text-primary">Manufacturing operations</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Production</h1><p className="mt-2 max-w-2xl text-muted-foreground">Track active drones, assigned work, component traceability, and completion decisions.</p></header>{!currentUser ? <AccessError message={apiError} /> : canRead ? <WorkflowPanel permissions={currentUser.permission_codes} roleCodes={currentUser.role_codes} scope="production" /> : <UnavailableWorkspace />}</div></AppShell>;
}

function AccessError({ message }: { message: string }) { return <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm" role="alert">{message}</div>; }
function UnavailableWorkspace() { return <EmptyState title="Production workspace unavailable" description="Your current role does not have access to production operations." action={<Button asChild variant="outline"><Link href="/dashboard">Return to overview</Link></Button>} />; }
