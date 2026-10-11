import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function MetricCard({
  label,
  value,
  context,
  href,
}: {
  label: string;
  value: number;
  context: string;
  href: string;
}) {
  return (
    <Card className="transition-shadow hover:shadow-md" size="sm">
      <CardHeader className="gap-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-3xl tracking-tight">{value}</CardTitle>
      </CardHeader>
      <CardContent>
        <Link className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline" href={href}>
          {context}
          <ArrowUpRight aria-hidden="true" className="size-3.5" />
        </Link>
      </CardContent>
    </Card>
  );
}
