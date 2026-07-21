import { apiBaseUrl, apiRequest, getAccessToken } from '../../services/apiClient';
import type { PaginatedResponse, ProductionDashboard, ProductionOrder, ProductionRequirement } from './types';

export async function fetchProductionDashboard(organizationId: string) {
  const params = new URLSearchParams({ organization_id: organizationId });
  return apiRequest<ProductionDashboard>(`${apiBaseUrl}/v1/production/dashboard?${params}`);
}

export async function listProductionOrders(params: { organizationId?: string; status?: string }) {
  const searchParams = new URLSearchParams({
    page: '1',
    page_size: '100',
    sort_by: 'updated_at',
    sort_direction: 'desc',
  });
  if (params.organizationId) searchParams.set('organization_id', params.organizationId);
  if (params.status) searchParams.set('status', params.status);
  return apiRequest<PaginatedResponse<ProductionOrder>>(
    `${apiBaseUrl}/v1/production/orders?${searchParams}`,
  );
}

export async function listProductionMaterials(orderId: string) {
  return apiRequest<ProductionRequirement[]>(
    `${apiBaseUrl}/v1/production/orders/${orderId}/materials`,
  );
}

export async function transitionProductionOrder(orderId: string, action: string, reason?: string) {
  return apiRequest<ProductionOrder>(`${apiBaseUrl}/v1/production/orders/${orderId}/${action}`, {
    body: JSON.stringify({ reason }),
    method: 'POST',
  });
}

export async function reserveMaterials(orderId: string) {
  return apiRequest<{ reserved_lines: number }>(
    `${apiBaseUrl}/v1/production/orders/${orderId}/reserve-materials`,
    {
      body: JSON.stringify({ lines: [] }),
      method: 'POST',
    },
  );
}

export async function downloadProductionOrder(orderId: string, format: 'pdf' | 'xlsx') {
  const response = await fetch(`${apiBaseUrl}/v1/production/orders/${orderId}/export/${format}`, {
    credentials: 'include',
    headers: getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : undefined,
  });
  if (!response.ok) throw new Error(response.statusText);
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match?.[1] ?? `production-order.${format}`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

