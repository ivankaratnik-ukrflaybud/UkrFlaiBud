import { apiBaseUrl, apiRequest } from '../../services/apiClient';
import type {
  Category,
  DocumentLine,
  InventoryDocument,
  Item,
  Location,
  Lot,
  PaginatedResponse,
  Serial,
  Site,
  StockBalance,
  Unit,
  Warehouse,
} from './types';

export type InventoryKind =
  | 'sites'
  | 'warehouses'
  | 'locations'
  | 'units'
  | 'categories'
  | 'items'
  | 'documents'
  | 'stock'
  | 'lots'
  | 'serials';

export interface ListParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortDirection?: 'asc' | 'desc';
  filters?: Record<string, string | boolean | null | undefined>;
}

export type InventoryMap = {
  sites: Site;
  warehouses: Warehouse;
  locations: Location;
  units: Unit;
  categories: Category;
  items: Item;
  documents: InventoryDocument;
  stock: StockBalance;
  lots: Lot;
  serials: Serial;
};

export async function listInventory<K extends InventoryKind>(
  kind: K,
  params: ListParams = {},
): Promise<PaginatedResponse<InventoryMap[K]>> {
  const searchParams = new URLSearchParams({
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 50),
    sort_by: params.sortBy ?? defaultSort(kind),
    sort_direction: params.sortDirection ?? 'desc',
  });

  Object.entries(params.filters ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });

  return apiRequest<PaginatedResponse<InventoryMap[K]>>(
    `${apiBaseUrl}/v1/inventory/${kind}?${searchParams.toString()}`,
  );
}

export async function createInventory<K extends Exclude<InventoryKind, 'stock'>>(
  kind: K,
  payload: Record<string, unknown>,
): Promise<InventoryMap[K]> {
  return apiRequest<InventoryMap[K]>(`${apiBaseUrl}/v1/inventory/${kind}`, {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function updateInventory<K extends Exclude<InventoryKind, 'stock'>>(
  kind: K,
  id: string,
  payload: Record<string, unknown>,
): Promise<InventoryMap[K]> {
  return apiRequest<InventoryMap[K]>(`${apiBaseUrl}/v1/inventory/${kind}/${id}`, {
    body: JSON.stringify(payload),
    method: 'PATCH',
  });
}

export async function deleteInventory(kind: Exclude<InventoryKind, 'stock'>, id: string) {
  await apiRequest<void>(`${apiBaseUrl}/v1/inventory/${kind}/${id}`, { method: 'DELETE' });
}

export async function addDocumentLine(documentId: string, payload: Record<string, unknown>) {
  return apiRequest<DocumentLine>(`${apiBaseUrl}/v1/inventory/documents/${documentId}/lines`, {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function listDocumentLines(documentId: string) {
  return apiRequest<DocumentLine[]>(`${apiBaseUrl}/v1/inventory/documents/${documentId}/lines`);
}

export async function postDocument(documentId: string) {
  return apiRequest<InventoryDocument>(`${apiBaseUrl}/v1/inventory/documents/${documentId}/post`, {
    method: 'POST',
  });
}

export async function cancelDocument(documentId: string, reason: string) {
  return apiRequest<InventoryDocument>(
    `${apiBaseUrl}/v1/inventory/documents/${documentId}/cancel`,
    {
      body: JSON.stringify({ reason }),
      method: 'POST',
    },
  );
}

export async function lowStock(organizationId: string) {
  return apiRequest<
    Array<{ item_id: string; sku: string; name: string; quantity: string; minimum_stock: string }>
  >(`${apiBaseUrl}/v1/inventory/low-stock?organization_id=${organizationId}`);
}

function defaultSort(kind: InventoryKind) {
  if (kind === 'documents') {
    return 'document_date';
  }
  if (kind === 'stock') {
    return 'updated_at';
  }
  return 'created_at';
}
