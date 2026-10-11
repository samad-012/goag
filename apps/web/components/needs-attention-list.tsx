import Link from "next/link";
import { AlertCircle, ArrowRight, CheckCircle2, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export type AttentionItem = {
  label: string;
  detail: string;
  href: string;
  severity: "attention" | "blocked" | "info" | "clear";
};

const severityConfig = {
  attention: { label: "Review", icon: AlertCircle, className: "text-amber-700" },
  blocked: { label: "Blocked", icon: AlertCircle, className: "text-destructive" },
  info: { label: "Today", icon: Info, className: "text-blue-700" },
  clear: { label: "Clear", icon: CheckCircle2, className: "text-emerald-700" },
} as const;

export function NeedsAttentionList({ items }: { items: AttentionItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Needs attention</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.map((item) => {
          const config = severityConfig[item.severity];
          const Icon = config.icon;
          return (
            <Link className="flex items-start gap-3 rounded-xl border border-transparent p-3 transition-colors hover:border-border hover:bg-muted/60" href={item.href} key={`${item.label}-${item.detail}`}>
              <Icon aria-hidden="true" className={`mt-0.5 size-4 shrink-0 ${config.className}`} />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{item.label}</span>
                  <Badge className="text-[11px]" variant={item.severity === "blocked" ? "destructive" : "outline"}>{config.label}</Badge>
                </span>
                <span className="mt-1 block text-xs text-muted-foreground">{item.detail}</span>
              </span>
              <ArrowRight aria-hidden="true" className="mt-1 size-4 shrink-0 text-muted-foreground" />
            </Link>
          );
        })}
      </CardContent>
    </Card>
  );
}
