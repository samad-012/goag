import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { EmailPanel } from "@/components/email-panel";
import { Button } from "@/components/ui/button";
import { getDashboardContext } from "@/lib/dashboard-context";

export default async function MailboxPage() {
  const { currentUser, apiError } = await getDashboardContext();
  const canRead = currentUser?.permission_codes.includes("mailbox.read") ?? false;
  return <AppShell activeKey="mailbox" currentUser={currentUser}><div className="space-y-6"><header><p className="text-sm font-medium text-primary">Shared communication</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">GOAG mailbox</h1><p className="mt-2 max-w-2xl text-muted-foreground">Read and send messages from the single shared GOAG mailbox.</p></header>{!currentUser ? <AccessError message={apiError} /> : canRead ? <EmailPanel permissions={currentUser.permission_codes} /> : <EmptyState title="Mailbox access unavailable" description="Only the Managing Director and Store Manager can access the shared GOAG mailbox." action={<Button asChild variant="outline"><Link href="/dashboard">Return to overview</Link></Button>} />}</div></AppShell>;
}

function AccessError({ message }: { message: string }) { return <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm" role="alert">{message}</div>; }
