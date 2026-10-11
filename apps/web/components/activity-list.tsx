import { Activity, Clock3 } from "lucide-react";
import type { DashboardAuditEvent } from "@/components/role-overview";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function readableAction(action: string): string {
  const labels: Record<string, string> = {
    "email.inbox_listed": "Mailbox viewed",
    "email.message_sent": "Message sent",
    "email.thread_read": "Message opened",
    "members.auth_linked": "Team member connected",
    "inventory.unit_received": "Inventory received",
    "inventory.component_issued": "Components issued",
    "drone.created": "Drone created",
  };
  return labels[action] ?? "Operational activity";
}

function readableEntity(entityType: string): string {
  return entityType.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function ActivityList({ events }: { events: DashboardAuditEvent[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Activity aria-hidden="true" className="size-4 text-primary" />Recent activity</CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {events.length ? events.map((event, index) => (
          <div className="flex items-start gap-3 rounded-xl p-3 hover:bg-muted/50" key={`${event.action}-${event.created_at}-${index}`}>
            <Clock3 aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{event.action_label ?? readableAction(event.action)}</p>
              <p className="mt-1 text-xs text-muted-foreground">{event.subject ?? readableEntity(event.entity_type)} · {formatDate(event.created_at)}</p>
            </div>
            <Badge variant="secondary">{event.status_label ?? "Updated"}</Badge>
          </div>
        )) : <p className="rounded-xl bg-muted/50 p-4 text-sm text-muted-foreground">Your recent operational activity will appear here.</p>}
      </CardContent>
    </Card>
  );
}
