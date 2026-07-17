import type { EntityKind } from './api';
import type { EmployeeStatus } from './types';

export type FieldType =
  | 'text'
  | 'email'
  | 'date'
  | 'boolean'
  | 'organization'
  | 'department'
  | 'position'
  | 'employee'
  | 'status';

export interface FieldConfig {
  name: string;
  type: FieldType;
  required?: boolean;
  multiline?: boolean;
}

export interface PageConfig {
  kind: EntityKind;
  titleKey: string;
  createKey: string;
  fields: FieldConfig[];
  columns: string[];
  filters: FieldConfig[];
  defaultSort: string;
}

export const emptyOption = '';

export const employeeStatuses: EmployeeStatus[] = ['active', 'on_leave', 'terminated'];

export const pageConfigs: Record<EntityKind, PageConfig> = {
  organizations: {
    kind: 'organizations',
    titleKey: 'organizations:pages.organizations',
    createKey: 'organizations:actions.createOrganization',
    defaultSort: 'name',
    fields: [
      { name: 'name', type: 'text', required: true },
      { name: 'short_name', type: 'text', required: true },
      { name: 'legal_name', type: 'text', required: true },
      { name: 'edrpou', type: 'text', required: true },
      { name: 'tax_number', type: 'text' },
      { name: 'email', type: 'email' },
      { name: 'phone', type: 'text' },
      { name: 'website', type: 'text' },
      { name: 'address', type: 'text', multiline: true },
      { name: 'is_active', type: 'boolean' },
    ],
    columns: ['name', 'short_name', 'edrpou', 'is_active', 'version'],
    filters: [
      { name: 'name', type: 'text' },
      { name: 'edrpou', type: 'text' },
      { name: 'is_active', type: 'boolean' },
    ],
  },
  departments: {
    kind: 'departments',
    titleKey: 'organizations:pages.departments',
    createKey: 'organizations:actions.createDepartment',
    defaultSort: 'name',
    fields: [
      { name: 'organization_id', type: 'organization', required: true },
      { name: 'parent_department_id', type: 'department' },
      { name: 'name', type: 'text', required: true },
      { name: 'code', type: 'text' },
      { name: 'description', type: 'text', multiline: true },
      { name: 'manager_employee_id', type: 'employee' },
      { name: 'is_active', type: 'boolean' },
    ],
    columns: ['name', 'code', 'organization_id', 'parent_department_id', 'is_active', 'version'],
    filters: [
      { name: 'organization_id', type: 'organization' },
      { name: 'parent_department_id', type: 'department' },
      { name: 'name', type: 'text' },
      { name: 'code', type: 'text' },
      { name: 'is_active', type: 'boolean' },
    ],
  },
  positions: {
    kind: 'positions',
    titleKey: 'organizations:pages.positions',
    createKey: 'organizations:actions.createPosition',
    defaultSort: 'name',
    fields: [
      { name: 'organization_id', type: 'organization', required: true },
      { name: 'department_id', type: 'department' },
      { name: 'name', type: 'text', required: true },
      { name: 'code', type: 'text' },
      { name: 'description', type: 'text', multiline: true },
      { name: 'is_active', type: 'boolean' },
    ],
    columns: ['name', 'code', 'organization_id', 'department_id', 'is_active', 'version'],
    filters: [
      { name: 'organization_id', type: 'organization' },
      { name: 'department_id', type: 'department' },
      { name: 'name', type: 'text' },
      { name: 'code', type: 'text' },
      { name: 'is_active', type: 'boolean' },
    ],
  },
  employees: {
    kind: 'employees',
    titleKey: 'organizations:pages.employees',
    createKey: 'organizations:actions.createEmployee',
    defaultSort: 'last_name',
    fields: [
      { name: 'organization_id', type: 'organization', required: true },
      { name: 'department_id', type: 'department' },
      { name: 'position_id', type: 'position' },
      { name: 'personnel_number', type: 'text' },
      { name: 'first_name', type: 'text', required: true },
      { name: 'last_name', type: 'text', required: true },
      { name: 'middle_name', type: 'text' },
      { name: 'email', type: 'email' },
      { name: 'phone', type: 'text' },
      { name: 'hire_date', type: 'date' },
      { name: 'termination_date', type: 'date' },
      { name: 'status', type: 'status', required: true },
      { name: 'supervisor_employee_id', type: 'employee' },
      { name: 'notes', type: 'text', multiline: true },
    ],
    columns: ['last_name', 'first_name', 'personnel_number', 'department_id', 'status', 'version'],
    filters: [
      { name: 'organization_id', type: 'organization' },
      { name: 'department_id', type: 'department' },
      { name: 'position_id', type: 'position' },
      { name: 'supervisor_employee_id', type: 'employee' },
      { name: 'status', type: 'status' },
      { name: 'name', type: 'text' },
    ],
  },
};
