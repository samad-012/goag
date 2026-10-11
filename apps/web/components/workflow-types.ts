export type Component = {
  id: string;
  code: string;
  name: string;
  category: string;
  serialized: boolean;
  status: string;
  minimum_stock: number;
  storage_location: string;
  remarks: string;
};

export type Drone = {
  id: string;
  drone_model_id: string | null;
  serial_number: string | null;
  status: string;
  notes: string | null;
  created_at: string;
};

export type DroneModel = { id: string; code: string; name: string; status: string };

export type RequestItem = {
  id: string;
  component_id: string;
  component_code?: string | null;
  component_name?: string | null;
  requested_quantity: number;
  issued_quantity: number;
  pending_quantity: number;
  status: string;
};

export type ComponentRequest = { id: string; drone_id: string; drone_serial_number?: string | null; status: string; items: RequestItem[]; created_at: string };

export type InventoryUnit = { id: string; component_id: string; serial_number: string | null; status: string; location: string; condition: string };

export type Installation = {
  id: string;
  drone_id: string;
  drone_serial_number?: string | null;
  inventory_unit_id: string;
  component_code?: string | null;
  component_name?: string | null;
  component_serial_number?: string | null;
  action: string;
  performed_by_membership_id: string;
  approved_by_membership_id: string | null;
  replacement_for_id: string | null;
  reason: string | null;
  occurred_at: string;
};

export type ProductionTask = {
  id: string;
  drone_id: string;
  drone_serial_number?: string | null;
  title: string;
  status: string;
  assigned_to_membership_id: string | null;
  assignee_display_name?: string | null;
  notes: string | null;
  completed_at: string | null;
  created_at: string;
};

export type Assignee = { membership_id: string; display_name: string; email: string };

export type DroneForm = { drone_model_id: string; new_model_name: string; new_model_code: string; serial_number: string; notes: string };
export type RequestForm = { drone_id: string; component_id: string; new_component_name: string; new_component_code: string; new_component_category: string; quantity: string };
export type IssueForm = { request_item_id: string; quantity: string; serial_numbers: string; substituted_component_id: string };
export type ActionForm = { drone_id: string; inventory_unit_id: string; action: string; replacement_for_id: string; reason: string };
export type TaskForm = { drone_id: string; title: string; assigned_to_membership_id: string; notes: string };
export type ConfirmationCheck = { key: string; label: string };

export const confirmationChecks: ConfirmationCheck[] = [
  { key: "required_components_installed", label: "Required components installed" },
  { key: "component_quantities_correct", label: "Component quantities correct" },
  { key: "serial_numbers_recorded", label: "Serial numbers recorded" },
  { key: "production_tasks_completed", label: "Production tasks completed" },
  { key: "component_issues_resolved", label: "No unresolved component issues" },
  { key: "drone_serial_exists", label: "Drone serial number exists" },
  { key: "quality_checklist_completed", label: "Basic quality checklist completed" },
];
