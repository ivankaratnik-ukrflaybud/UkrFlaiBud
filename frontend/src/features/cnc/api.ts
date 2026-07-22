import { apiBaseUrl, apiRequest, getAccessToken } from '../../services/apiClient';
import type {
  CncDashboard,
  CncMachine,
  CncMaterialTransaction,
  CncOutput,
  CncPart,
  CncProgram,
  CncReadiness,
  CncSheetPlan,
  CncWorkOrder,
  PaginatedResponse,
} from './types';

const pageParams = {
  page: '1',
  page_size: '100',
};

function params(values: Record<string, string | undefined>) {
  const search = new URLSearchParams(pageParams);
  Object.entries(values).forEach(([key, value]) => {
    if (value) search.set(key, value);
  });
  return search;
}

export async function fetchCncDashboard(organizationId: string) {
  return apiRequest<CncDashboard>(
    `${apiBaseUrl}/v1/cnc/dashboard?${new URLSearchParams({ organization_id: organizationId })}`,
  );
}

export async function listCncMachines(organizationId?: string) {
  return apiRequest<PaginatedResponse<CncMachine>>(
    `${apiBaseUrl}/v1/cnc/machines?${params({ organization_id: organizationId })}`,
  );
}

export async function listCncPrograms(organizationId?: string) {
  return apiRequest<PaginatedResponse<CncProgram>>(
    `${apiBaseUrl}/v1/cnc/programs?${params({ organization_id: organizationId })}`,
  );
}

export async function listCncParts(organizationId?: string) {
  return apiRequest<PaginatedResponse<CncPart>>(
    `${apiBaseUrl}/v1/cnc/parts?${params({ organization_id: organizationId })}`,
  );
}

export async function listCncSheetPlans(organizationId?: string) {
  return apiRequest<PaginatedResponse<CncSheetPlan>>(
    `${apiBaseUrl}/v1/cnc/sheet-plans?${params({ organization_id: organizationId })}`,
  );
}

export async function listCncWorkOrders(organizationId?: string, status?: string) {
  return apiRequest<PaginatedResponse<CncWorkOrder>>(
    `${apiBaseUrl}/v1/cnc/work-orders?${params({ organization_id: organizationId, status })}`,
  );
}

export async function listCncQueue(organizationId?: string) {
  return apiRequest<PaginatedResponse<CncWorkOrder>>(
    `${apiBaseUrl}/v1/cnc/queue?${params({ organization_id: organizationId })}`,
  );
}

export async function listCncOutputs(workOrderId: string) {
  return apiRequest<CncOutput[]>(`${apiBaseUrl}/v1/cnc/work-orders/${workOrderId}/outputs`);
}

export async function listCncMaterialTransactions(workOrderId: string) {
  return apiRequest<CncMaterialTransaction[]>(
    `${apiBaseUrl}/v1/cnc/work-orders/${workOrderId}/material`,
  );
}

export async function fetchReadiness(workOrderId: string) {
  return apiRequest<CncReadiness>(`${apiBaseUrl}/v1/cnc/work-orders/${workOrderId}/readiness`);
}

export async function cncAction(workOrderId: string, action: string, reason?: string) {
  return apiRequest<CncWorkOrder>(`${apiBaseUrl}/v1/cnc/work-orders/${workOrderId}/${action}`, {
    body: reason ? JSON.stringify({ reason, status: 'queued' }) : undefined,
    method: 'POST',
  });
}

export async function reportCncOutput(workOrderId: string, goodQuantity: string, rejectedQuantity: string) {
  return apiRequest<CncWorkOrder>(`${apiBaseUrl}/v1/cnc/work-orders/${workOrderId}/report-output`, {
    body: JSON.stringify({ good_quantity: goodQuantity, rejected_quantity: rejectedQuantity }),
    method: 'POST',
  });
}

export async function issueCncMaterial(workOrderId: string, quantity: string) {
  return apiRequest(`${apiBaseUrl}/v1/cnc/work-orders/${workOrderId}/material-issue`, {
    body: JSON.stringify({ quantity }),
    method: 'POST',
  });
}

export async function downloadCncWorkOrder(workOrderId: string, format: 'pdf' | 'xlsx') {
  const response = await fetch(`${apiBaseUrl}/v1/cnc/work-orders/${workOrderId}/export/${format}`, {
    credentials: 'include',
    headers: getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : undefined,
  });
  if (!response.ok) throw new Error(response.statusText);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `cnc-work-order.${format}`;
  link.click();
  URL.revokeObjectURL(url);
}
