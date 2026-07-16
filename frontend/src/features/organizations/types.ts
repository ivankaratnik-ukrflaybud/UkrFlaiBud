export type SortDirection = 'asc' | 'desc';

export type EmployeeStatus = 'active' | 'on_leave' | 'terminated';

export interface EntityBase {
  id: string;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  version: number;
}

export interface Organization extends EntityBase {
  name: string;
  short_name: string;
  legal_name: string;
  edrpou: string;
  tax_number: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address: string | null;
  is_active: boolean;
}

export interface Department extends EntityBase {
  organization_id: string;
  parent_department_id: string | null;
  name: string;
  code: string | null;
  description: string | null;
  manager_employee_id: string | null;
  is_active: boolean;
}

export interface Position extends EntityBase {
  organization_id: string;
  department_id: string | null;
  name: string;
  code: string | null;
  description: string | null;
  is_active: boolean;
}

export interface Employee extends EntityBase {
  organization_id: string;
  department_id: string | null;
  position_id: string | null;
  personnel_number: string | null;
  first_name: string;
  last_name: string;
  middle_name: string | null;
  email: string | null;
  phone: string | null;
  hire_date: string | null;
  termination_date: string | null;
  status: EmployeeStatus;
  supervisor_employee_id: string | null;
  notes: string | null;
}

export type OrganizationEntity = Organization | Department | Position | Employee;

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
  correlation_id: string | null;
}
