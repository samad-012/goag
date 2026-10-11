export type WorkspaceNavItem = {
  key: string;
  label: string;
  description: string;
  href: string;
  icon: "overview" | "inventory" | "production" | "attendance" | "sales" | "mailbox" | "team";
  requiredPermissions?: string[];
};

const ROLE_LABELS: Record<string, string> = {
  MANAGING_DIRECTOR: "Managing Director",
  PRODUCTION_MANAGER: "Production Manager",
  STORE_MANAGER: "Store Manager",
  SALES_MANAGER: "Sales Manager",
  TECHNICIAN: "Technician",
  AFTER_SALES_MANAGER: "After-Sales Manager",
};

export const workspaceNavigation: WorkspaceNavItem[] = [
  {
    key: "overview",
    label: "Overview",
    description: "Your operational control tower",
    href: "/dashboard",
    icon: "overview",
  },
  {
    key: "inventory",
    label: "Inventory",
    description: "Stock, requests, and component traceability",
    href: "/dashboard/inventory",
    icon: "inventory",
    requiredPermissions: ["inventory.read"],
  },
  {
    key: "production",
    label: "Production",
    description: "Drones, tasks, and completion",
    href: "/dashboard/production",
    icon: "production",
    requiredPermissions: ["drone.read"],
  },
  {
    key: "attendance",
    label: "Attendance",
    description: "Your attendance and manager controls",
    href: "/dashboard/attendance",
    icon: "attendance",
  },
  {
    key: "sales",
    label: "Sales",
    description: "Customers, orders, and deliveries",
    href: "/dashboard/sales",
    icon: "sales",
    requiredPermissions: ["sales.manage"],
  },
  {
    key: "mailbox",
    label: "Mailbox",
    description: "The shared GOAG mailbox",
    href: "/dashboard/mailbox",
    icon: "mailbox",
    requiredPermissions: ["mailbox.read"],
  },
  {
    key: "team",
    label: "Team & admin",
    description: "Users, roles, and access",
    href: "/dashboard/team",
    icon: "team",
    requiredPermissions: ["members.read"],
  },
];

export function roleLabel(roleCode: string): string {
  return ROLE_LABELS[roleCode] ?? "GOAG team member";
}

export function roleLabels(roleCodes: string[]): string[] {
  return roleCodes.map(roleLabel);
}

export function canAccessNavigation(item: WorkspaceNavItem, permissions: string[]): boolean {
  return !item.requiredPermissions?.length || item.requiredPermissions.some((permission) => permissions.includes(permission));
}

export function getVisibleNavigation(permissions: string[]): WorkspaceNavItem[] {
  return workspaceNavigation.filter((item) => canAccessNavigation(item, permissions));
}

export function hasAnyPermission(permissions: string[], requiredPermissions: string[]): boolean {
  return requiredPermissions.some((permission) => permissions.includes(permission));
}
