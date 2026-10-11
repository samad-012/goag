import { AppShell } from "@/components/app-shell";
import { AttendancePanel } from "@/components/attendance-panel";
import { getDashboardContext } from "@/lib/dashboard-context";

export default async function AttendancePage() {
  const { currentUser, apiError } = await getDashboardContext();
  return <AppShell activeKey="attendance" currentUser={currentUser}><div className="space-y-6"><header><p className="text-sm font-medium text-primary">People operations</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Attendance</h1><p className="mt-2 max-w-2xl text-muted-foreground">Check in from your registered device and review your attendance history.</p></header>{currentUser ? <AttendancePanel permissions={currentUser.permission_codes} /> : <AccessError message={apiError} />}</div></AppShell>;
}

function AccessError({ message }: { message: string }) { return <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm" role="alert">{message}</div>; }
