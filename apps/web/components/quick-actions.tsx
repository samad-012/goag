import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function QuickActions({ actions }: { actions: { label: string; href: string }[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => (
        <Button asChild key={action.label} variant="default">
          <Link href={action.href}>{action.label}<ArrowRight aria-hidden="true" /></Link>
        </Button>
      ))}
    </div>
  );
}
