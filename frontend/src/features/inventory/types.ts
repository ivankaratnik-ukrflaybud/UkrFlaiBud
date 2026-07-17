export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface Site {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  is_active: boolean;
  version: number;
}

export interface Warehouse {
  id: string;
  organization_id: string;
  site_id: string;
  code: string;
  name: string;
  warehouse_type: string;
  allow_negative_stock: boolean;
  is_active: boolean;
  version: number;
}

export interface Location {
  id: string;
  organization_id: string;
  warehouse_id: string;
  parent_id?: string | null;
  code: string;
  name: string;
  location_type: string;
  is_active: boolean;
  version: number;
}

export interface Unit {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  symbol: string;
  precision: number;
  is_active: boolean;
  version: number;
}

export interface Category {
  id: string;
  organization_id: string;
  parent_id?: string | null;
  code: string;
  name: string;
  is_active: boolean;
  version: number;
}

export interface Item {
  id: string;
  organization_id: string;
  sku: string;
  name: string;
  category_id: string;
  unit_of_measure_id: string;
  item_type: string;
  barcode?: string | null;
  track_lots: boolean;
  track_serial_numbers: boolean;
  minimum_stock: string;
  maximum_stock?: string | null;
  default_warehouse_id?: string | null;
  is_active: boolean;
  version: number;
}

export interface StockBalance {
  id: string;
  organization_id: string;
  item_id: string;
  warehouse_id: string;
  location_id?: string | null;
  lot_id?: string | null;
  quantity: string;
  updated_at: string;
}

export interface InventoryDocument {
  id: string;
  organization_id: string;
  document_number: string;
  document_type: string;
  status: string;
  document_date: string;
  source_warehouse_id?: string | null;
  destination_warehouse_id?: string | null;
  responsible_employee_id?: string | null;
  notes?: string | null;
  version: number;
}

export interface DocumentLine {
  id: string;
  document_id: string;
  line_number: number;
  item_id: string;
  quantity: string;
  version: number;
}

export interface Lot {
  id: string;
  item_id: string;
  lot_number: string;
  expires_at?: string | null;
  is_active: boolean;
}

export interface Serial {
  id: string;
  item_id: string;
  serial_number: string;
  status: string;
  current_warehouse_id?: string | null;
}
