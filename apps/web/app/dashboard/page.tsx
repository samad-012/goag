import { getDashboardContext } from "@/lib/dashboard-context";
import { AppShell } from "@/components/app-shell";
import { RoleOverview } from "@/components/role-overview";
import { roleLabels } from "@/lib/workspace-config";

export default async function DashboardPage() {
  const { currentUser, apiError } = await getDashboardContext();
  const roleText = currentUser ? roleLabels(currentUser.role_codes).join(" · ") : "GOAG workspace";

  return (
    <AppShell currentUser={currentUser}>
      <div className="flex flex-col gap-8">
        <header className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-medium text-primary">{roleText}</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Good to see you, {currentUser?.user.display_name ?? "GOAG team member"}</h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">Here&apos;s what needs your attention across the GOAG operations workspace today.</p>
          </div>
          <p className="text-sm text-muted-foreground">Today&apos;s operational view</p>
        </header>

        {!currentUser ? (
          <section className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5" role="alert">
            <h2 className="font-semibold">Workspace access unavailable</h2>
            <p className="mt-2 text-sm">{apiError}</p>
            <p className="mt-1 text-sm text-muted-foreground">Start the FastAPI service, then refresh this page.</p>
          </section>
        ) : <RoleOverview currentUser={currentUser} />}
      </div>
    </AppShell>
  );
}
