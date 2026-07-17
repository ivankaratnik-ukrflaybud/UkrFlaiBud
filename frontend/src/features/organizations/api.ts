import { apiBaseUrl, apiRequest } from '../../services/apiClient';
import type {
  Department,
  Employee,
  Organization,
  PaginatedResponse,
  Position,
  SortDirection,
} from './types';

export type EntityKind = 'organizations' | 'departments' | 'positions' | 'employees';

export interface ListParams {
  page: number;
  pageSize: number;
  sortBy: string;
  sortDirection: SortDirection;
  filters: Record<string, string | boolean | null | undefined>;
}

export type EntityMap = {
  organizations: Organization;
  departments: Department;
  positions: Position;
  employees: Employee;
};

export async function listEntities<K extends EntityKind>(
  kind: K,
  params: ListParams,
): Promise<PaginatedResponse<EntityMap[K]>> {
  const searchParams = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
    sort_by: params.sortBy,
    sort_direction: params.sortDirection,
  });

  Object.entries(params.filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });

  return apiRequest<PaginatedResponse<EntityMap[K]>>(`${pathFor(kind)}?${searchParams.toString()}`);
}

export async function createEntity<K extends EntityKind>(
  kind: K,
  payload: Record<string, unknown>,
): Promise<EntityMap[K]> {
  return apiRequest<EntityMap[K]>(pathFor(kind), {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function updateEntity<K extends EntityKind>(
  kind: K,
  id: string,
  payload: Record<string, unknown>,
): Promise<EntityMap[K]> {
  return apiRequest<EntityMap[K]>(`${pathFor(kind)}/${id}`, {
    body: JSON.stringify(payload),
    method: 'PATCH',
  });
}

export async function deleteEntity(kind: EntityKind, id: string): Promise<void> {
  await apiRequest<void>(`${pathFor(kind)}/${id}`, { method: 'DELETE' });
}

function pathFor(kind: EntityKind): string {
  return `${apiBaseUrl}/v1/${kind}`;
}
