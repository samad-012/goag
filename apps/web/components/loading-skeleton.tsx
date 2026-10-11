import { Card } from "@/components/ui/card";

export function LoadingSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div aria-label="Loading workspace" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }, (_, index) => (
        <Card aria-hidden="true" className="gap-3 p-4" key={index} size="sm">
          <div className="h-3 w-24 animate-pulse rounded bg-muted" />
          <div className="h-7 w-16 animate-pulse rounded bg-muted" />
          <div className="h-3 w-32 animate-pulse rounded bg-muted" />
        </Card>
      ))}
    </div>
  );
}
