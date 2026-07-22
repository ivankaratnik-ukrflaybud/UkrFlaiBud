export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface CncDashboard {
  running_machines: number;
  available_machines: number;
  queued_work_orders: number;
  running_work_orders: number;
  blocked_work_orders: number;
  overdue_work_orders: number;
  completed_today: number;
  rejected_today: string;
}

export interface CncMachine {
  id: string;
  code: string;
  name: string;
  machine_type: string;
  status: string;
  site_id: string;
  is_active: boolean;
}

export interface CncProgram {
  id: string;
  code: string;
  name: string;
  revision: string;
  file_type: string;
  program_status: string;
}

export interface CncPart {
  id: string;
  code: string;
  name: string;
  material_name_snapshot?: string | null;
  drawing_revision?: string | null;
}

export interface CncSheetPlan {
  id: string;
  plan_number: string;
  name: string;
  status: string;
  material_name_snapshot: string;
  planned_sheet_quantity: string;
}

export interface CncWorkOrder {
  id: string;
  work_order_number: string;
  name: string;
  status: string;
  priority: string;
  part_name_snapshot?: string | null;
  material_name_snapshot?: string | null;
  planned_quantity: string;
  completed_quantity: string;
  rejected_quantity: string;
  queue_position?: number | null;
  machine_id?: string | null;
  operator_employee_id?: string | null;
  planned_start_at?: string | null;
}

export interface CncOutput {
  id: string;
  part_code_snapshot: string;
  part_name_snapshot: string;
  planned_quantity: string;
  completed_quantity: string;
  rejected_quantity: string;
  output_inventory_document_id?: string | null;
}

export interface CncMaterialTransaction {
  id: string;
  work_order_id: string;
  transaction_type: string;
  inventory_document_id: string;
  material_item_id: string;
  warehouse_id: string;
  location_id?: string | null;
  lot_id?: string | null;
  quantity: string;
  reason?: string | null;
  posted_at: string;
  created_at: string;
}

export interface ReadinessItem {
  code: string;
  label: string;
  ready: boolean;
}

export interface CncReadiness {
  work_order_id: string;
  ready: boolean;
  checklist: ReadinessItem[];
}
