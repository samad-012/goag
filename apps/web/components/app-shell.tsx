import Link from "next/link";
import {
  Boxes,
  CalendarClock,
  ChevronDown,
  ClipboardList,
  Factory,
  LayoutDashboard,
  Mail,
  Menu,
  ShieldCheck,
  ShoppingBag,
  Users,
} from "lucide-react";
import type { CurrentUserResponse } from "@/lib/api-client";
import { getVisibleNavigation, roleLabels, type WorkspaceNavItem } from "@/lib/workspace-config";
import { WorkspaceControls } from "@/components/workspace-controls";

const iconMap = {
  overview: LayoutDashboard,
  inventory: Boxes,
  production: Factory,
  attendance: CalendarClock,
  sales: ShoppingBag,
  mailbox: Mail,
  team: Users,
} as const;

function NavigationLinks({ items, activeKey }: { items: WorkspaceNavItem[]; activeKey: string }) {
  return (
    <nav aria-label="Workspace navigation" className="space-y-1">
      {items.map((item) => {
        const Icon = iconMap[item.icon];
        const active = item.key === activeKey;
        return (
          <Link
            aria-current={active ? "page" : undefined}
            className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
              active
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-sidebar-foreground/75 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            }`}
            href={item.href}
            key={item.key}
            title={item.description}
          >
            <Icon aria-hidden="true" className="size-4 shrink-0" />
            <span className="truncate">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

function UserMenu({ currentUser }: { currentUser: CurrentUserResponse | null }) {
  const displayName = currentUser?.user.display_name ?? "GOAG user";
  const labels = currentUser ? roleLabels(currentUser.role_codes) : [];

  return (
    <details className="relative">
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-left shadow-sm outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
        <span className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          {displayName.slice(0, 1).toUpperCase()}
        </span>
        <span className="hidden min-w-0 sm:block">
          <span className="block max-w-40 truncate text-sm font-medium">{displayName}</span>
          <span className="block max-w-40 truncate text-xs text-muted-foreground">{labels.join(" · ") || "Workspace user"}</span>
        </span>
        <ChevronDown aria-hidden="true" className="size-4 text-muted-foreground" />
      </summary>
      <div className="absolute right-0 z-30 mt-2 w-64 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-card p-3 shadow-lg">
        <p className="text-sm font-medium">{displayName}</p>
        <p className="mt-1 text-xs text-muted-foreground">{labels.join(" · ") || "Workspace user"}</p>
        <div className="my-3 h-px bg-border" />
        <Link className="block rounded-lg px-2 py-2 text-sm hover:bg-muted" href="/">
          Home
        </Link>
        <Link className="mt-1 block rounded-lg px-2 py-2 text-sm text-destructive hover:bg-destructive/10" href="/logout">
          Sign out
        </Link>
      </div>
    </details>
  );
}

export function AppShell({
  children,
  currentUser,
  activeKey = "overview",
}: {
  children: React.ReactNode;
  currentUser: CurrentUserResponse | null;
  activeKey?: string;
}) {
  const permissions = currentUser?.permission_codes ?? [];
  const visibleNavigation = getVisibleNavigation(permissions);

  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-sidebar-border bg-sidebar px-4 py-5 lg:block">
        <div className="flex h-full flex-col">
          <Link className="flex items-center gap-3 px-2" href="/dashboard">
            <span className="flex size-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
              <ShieldCheck aria-hidden="true" className="size-5" />
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-wide text-sidebar-foreground">GOAG</span>
              <span className="block text-xs text-sidebar-foreground/60">Operations workspace</span>
            </span>
          </Link>

          <div className="mt-8">
            <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-sidebar-foreground/45">Workspace</p>
            <NavigationLinks activeKey={activeKey} items={visibleNavigation} />
          </div>

          <div className="mt-auto rounded-2xl border border-sidebar-border bg-sidebar-accent/60 p-3 text-xs text-sidebar-foreground/70">
            <div className="flex items-center gap-2 font-medium text-sidebar-foreground">
              <ClipboardList aria-hidden="true" className="size-4" />
              <span>Operational control tower</span>
            </div>
            <p className="mt-2 leading-5">Your navigation is filtered to the access assigned to your role.</p>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-border/80 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-3 px-4 sm:px-6 lg:px-8">
            <details className="relative lg:hidden">
              <summary className="flex size-9 cursor-pointer list-none items-center justify-center rounded-lg border border-border bg-card outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
                <Menu aria-hidden="true" className="size-4" />
                <span className="sr-only">Open workspace navigation</span>
              </summary>
              <div className="absolute left-0 top-11 z-30 max-h-[calc(100vh-5rem)] w-64 max-w-[calc(100vw-2rem)] overflow-y-auto rounded-xl border border-border bg-sidebar p-3 shadow-xl">
                <NavigationLinks activeKey={activeKey} items={visibleNavigation} />
              </div>
            </details>

            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-muted-foreground lg:hidden">GOAG Operations</p>
              <p className="hidden text-sm font-medium text-foreground lg:block">Operations workspace</p>
            </div>

            <WorkspaceControls />
            <UserMenu currentUser={currentUser} />
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      </div>
    </div>
  );
}
