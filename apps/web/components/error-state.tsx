import Link from "next/link";
import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ErrorState({
  title = "Operational data is unavailable",
  description,
  onRetry,
  secondaryHref,
  secondaryLabel,
}: {
  title?: string;
  description: string;
  onRetry: () => void;
  secondaryHref?: string;
  secondaryLabel?: string;
}) {
  return (
    <Card className="border-destructive/30 bg-destructive/[0.03]" role="alert">
      <CardHeader>
        <div className="flex size-10 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
          <AlertTriangle aria-hidden="true" className="size-5" />
        </div>
        <CardTitle className="mt-2">{title}</CardTitle>
        <CardDescription className="max-w-xl">{description}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button type="button" onClick={onRetry}>
          <RotateCw aria-hidden="true" />
          Retry
        </Button>
        {secondaryHref && secondaryLabel ? (
          <Button asChild type="button" variant="outline">
            <Link href={secondaryHref}>{secondaryLabel}</Link>
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
