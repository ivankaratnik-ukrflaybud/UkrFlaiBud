export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface ProductionOrder {
  id: string;
  order_number: string;
  name: string;
  product_item_id: string;
  bom_version_number: number;
  status: string;
  priority: string;
  site_id: string;
  planned_quantity: string;
  completed_quantity: string;
  rejected_quantity: string;
  planned_start_date?: string | null;
  planned_end_date?: string | null;
  responsible_employee_id?: string | null;
  version: number;
}

export interface ProductionDashboard {
  active_orders: number;
  planned: number;
  in_progress: number;
  partially_completed: number;
  overdue: number;
  with_material_shortage: number;
  completed_today: number;
  urgent_orders: ProductionOrder[];
  active_order_rows: ProductionOrder[];
}

export interface ProductionRequirement {
  id: string;
  line_number: number;
  item_code_snapshot?: string | null;
  display_name: string;
  planned_quantity: string;
  reserved_quantity: string;
  issued_quantity: string;
  returned_quantity: string;
  consumed_quantity: string;
  scrapped_quantity: string;
  unit_symbol_snapshot: string;
  source_type: string;
  is_optional: boolean;
  is_alternative: boolean;
  available_quantity: string;
  shortage_quantity: string;
  remaining_to_issue: string;
}

