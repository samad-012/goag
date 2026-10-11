import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { getDashboardContext } from "@/lib/dashboard-context";

export default async function SalesPage() {
  const { currentUser, apiError } = await getDashboardContext();
  const canRead = currentUser?.permission_codes.includes("sales.manage") ?? false;
  return <AppShell activeKey="sales" currentUser={currentUser}><div className="space-y-6"><header><p className="text-sm font-medium text-primary">Commercial operations</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Sales</h1><p className="mt-2 max-w-2xl text-muted-foreground">Customers, quotations, orders, deliveries, and sold-drone records.</p></header>{!currentUser ? <AccessError message={apiError} /> : canRead ? <EmptyState title="Sales workspace coming next" description="The Sales workspace is reserved for customers, quotations, orders, deliveries, and sold-drone records. Its API module is not implemented yet." action={<Button asChild variant="outline"><Link href="/dashboard">Return to overview</Link></Button>} /> : <EmptyState title="Sales workspace unavailable" description="Your current role does not have access to Sales operations." />}</div></AppShell>;
}

function AccessError({ message }: { message: string }) { return <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm" role="alert">{message}</div>; }
