import dayjs from 'dayjs';
import { z } from 'zod';

import { emptyOption, type PageConfig } from './config';
import type {
  Department,
  Employee,
  Organization,
  OrganizationEntity,
  Position,
} from './types';

export type FormValues = Record<string, string | boolean>;

export function schemaFor(config: PageConfig, t: (key: string) => string) {
  const shape: Record<string, z.ZodTypeAny> = {};
  config.fields.forEach((field) => {
    if (field.type === 'boolean') {
      shape[field.name] = z.boolean();
      return;
    }
    if (field.type === 'email') {
      shape[field.name] = field.required
        ? z.string().min(1, t('common:validation.required')).email(t('common:validation.invalidEmail'))
        : z.union([z.string().email(t('common:validation.invalidEmail')), z.literal(''), z.undefined()]);
      return;
    }
    shape[field.name] = field.required
      ? z.string().min(1, t('common:validation.required'))
      : z.string().optional();
  });
  return z.object(shape);
}

export function formValuesFor(config: PageConfig, entity: OrganizationEntity | null): FormValues {
  return Object.fromEntries(
    config.fields.map((field) => {
      if (field.type === 'boolean') {
        return [field.name, entity ? Boolean(valueFor(entity, field.name)) : true];
      }
      return [field.name, entity ? String(valueFor(entity, field.name) ?? emptyOption) : emptyOption];
    }),
  );
}

export function normalizePayload(
  config: PageConfig,
  values: FormValues,
  editing: OrganizationEntity | null,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  config.fields.forEach((field) => {
    const value = values[field.name];
    payload[field.name] = value === emptyOption && !field.required ? null : value;
  });
  if (editing) {
    payload.version = editing.version;
  }
  return payload;
}

export function valueFor(entity: OrganizationEntity, field: string): unknown {
  return (entity as unknown as Record<string, unknown>)[field];
}

export function formatValue(
  field: string,
  entity: OrganizationEntity,
  lookups: {
    departments: Department[];
    employees: Employee[];
    organizations: Organization[];
    positions: Position[];
    t: (key: string) => string;
  },
) {
  const value = valueFor(entity, field);
  if (value === null || value === undefined || value === '') {
    return lookups.t('organizations:values.empty');
  }
  if (field === 'is_active') {
    return value ? lookups.t('organizations:values.active') : lookups.t('organizations:values.inactive');
  }
  if (field === 'status') {
    return lookups.t(`organizations:statuses.${value}`);
  }
  if (field.endsWith('_at') || field.endsWith('_date')) {
    return dayjs(String(value)).format('DD.MM.YYYY');
  }
  if (field === 'organization_id') {
    return lookups.organizations.find((item) => item.id === value)?.name ?? String(value);
  }
  if (field === 'department_id' || field === 'parent_department_id') {
    return lookups.departments.find((item) => item.id === value)?.name ?? String(value);
  }
  if (field === 'position_id') {
    return lookups.positions.find((item) => item.id === value)?.name ?? String(value);
  }
  if (field === 'supervisor_employee_id' || field === 'manager_employee_id') {
    const employee = lookups.employees.find((item) => item.id === value);
    return employee ? `${employee.last_name} ${employee.first_name}` : String(value);
  }
  return String(value);
}

export function buildDepartmentTree(departments: Department[]) {
  const children = new Map<string | null, Department[]>();
  departments.forEach((department) => {
    const key = department.parent_department_id;
    children.set(key, [...(children.get(key) ?? []), department]);
  });
  const nodes: { department: Department; depth: number }[] = [];
  const visit = (parentId: string | null, depth: number) => {
    (children.get(parentId) ?? []).forEach((department) => {
      nodes.push({ department, depth });
      visit(department.id, depth + 1);
    });
  };
  visit(null, 0);
  return nodes;
}
