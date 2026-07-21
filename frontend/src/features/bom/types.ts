import type { PaginatedResponse } from '../inventory/types';

export type BomStatus = 'draft' | 'under_review' | 'approved' | 'archived';
export type BomVersionStatus = 'draft' | 'under_review' | 'approved' | 'superseded' | 'archived';
export type BomLineSourceType = 'inventory_item' | 'manual' | 'subassembly';

export interface BomSpecification {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  description?: string | null;
  product_item_id?: string | null;
  specification_type: string;
  status: BomStatus;
  current_version_number: number;
  effective_from?: string | null;
  effective_to?: string | null;
  notes?: string | null;
  is_active: boolean;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface BomVersion {
  id: string;
  bom_id: string;
  version_number: number;
  version_label?: string | null;
  status: BomVersionStatus;
  change_reason?: string | null;
  created_by_user_id: string;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface BomLine {
  id: string;
  bom_version_id: string;
  line_number: number;
  parent_line_id?: string | null;
  inventory_item_id?: string | null;
  position_code?: string | null;
  display_name: string;
  description?: string | null;
  quantity: string;
  unit_of_measure_id: string;
  waste_percentage: string;
  is_optional: boolean;
  is_alternative: boolean;
  alternative_group?: string | null;
  reference_designator?: string | null;
  drawing_number?: string | null;
  manufacturer?: string | null;
  manufacturer_part_number?: string | null;
  technical_requirements?: string | null;
  notes?: string | null;
  sort_order: number;
  source_type: BomLineSourceType;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface BomCompare {
  added: Array<Record<string, unknown>>;
  removed: Array<Record<string, unknown>>;
  changed: Array<Record<string, unknown>>;
}

export type BomListResponse = PaginatedResponse<BomSpecification>;
