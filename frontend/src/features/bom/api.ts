import { apiBaseUrl, apiRequest, getAccessToken } from '../../services/apiClient';
import type { BomCompare, BomLine, BomListResponse, BomSpecification, BomVersion } from './types';

export async function listBomSpecifications(params: {
  search?: string;
  status?: string;
  organizationId?: string;
}) {
  const searchParams = new URLSearchParams({
    page: '1',
    page_size: '100',
    sort_by: 'updated_at',
    sort_direction: 'desc',
  });
  if (params.search) searchParams.set('search', params.search);
  if (params.status) searchParams.set('status', params.status);
  if (params.organizationId) searchParams.set('organization_id', params.organizationId);
  return apiRequest<BomListResponse>(
    `${apiBaseUrl}/v1/bom/specifications?${searchParams.toString()}`,
  );
}

export async function createBomSpecification(payload: Record<string, unknown>) {
  return apiRequest<BomSpecification>(`${apiBaseUrl}/v1/bom/specifications`, {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function updateBomSpecification(id: string, payload: Record<string, unknown>) {
  return apiRequest<BomSpecification>(`${apiBaseUrl}/v1/bom/specifications/${id}`, {
    body: JSON.stringify(payload),
    method: 'PATCH',
  });
}

export async function copyBomSpecification(id: string, payload: Record<string, unknown>) {
  return apiRequest<BomSpecification>(`${apiBaseUrl}/v1/bom/specifications/${id}/copy`, {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function archiveBomSpecification(id: string) {
  return apiRequest<BomSpecification>(`${apiBaseUrl}/v1/bom/specifications/${id}/archive`, {
    method: 'POST',
  });
}

export async function getBomSpecification(id: string) {
  return apiRequest<BomSpecification>(`${apiBaseUrl}/v1/bom/specifications/${id}`);
}

export async function listBomVersions(specificationId: string) {
  return apiRequest<BomVersion[]>(`${apiBaseUrl}/v1/bom/specifications/${specificationId}/versions`);
}

export async function createBomVersion(specificationId: string, payload: Record<string, unknown>) {
  return apiRequest<BomVersion>(`${apiBaseUrl}/v1/bom/specifications/${specificationId}/versions`, {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function approveBomVersion(versionId: string) {
  return apiRequest<BomVersion>(`${apiBaseUrl}/v1/bom/versions/${versionId}/approve`, {
    method: 'POST',
  });
}

export async function archiveBomVersion(versionId: string) {
  return apiRequest<BomVersion>(`${apiBaseUrl}/v1/bom/versions/${versionId}/archive`, {
    method: 'POST',
  });
}

export async function listBomLines(versionId: string) {
  return apiRequest<BomLine[]>(`${apiBaseUrl}/v1/bom/versions/${versionId}/lines`);
}

export async function addBomLine(versionId: string, payload: Record<string, unknown>) {
  return apiRequest<BomLine>(`${apiBaseUrl}/v1/bom/versions/${versionId}/lines`, {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function updateBomLine(versionId: string, lineId: string, payload: Record<string, unknown>) {
  return apiRequest<BomLine>(`${apiBaseUrl}/v1/bom/versions/${versionId}/lines/${lineId}`, {
    body: JSON.stringify(payload),
    method: 'PATCH',
  });
}

export async function deleteBomLine(versionId: string, lineId: string) {
  return apiRequest<void>(`${apiBaseUrl}/v1/bom/versions/${versionId}/lines/${lineId}`, {
    method: 'DELETE',
  });
}

export async function duplicateBomLine(versionId: string, lineId: string) {
  return apiRequest<BomLine>(
    `${apiBaseUrl}/v1/bom/versions/${versionId}/lines/${lineId}/duplicate`,
    { method: 'POST' },
  );
}

export async function reorderBomLines(versionId: string, lineIds: string[]) {
  return apiRequest<BomLine[]>(`${apiBaseUrl}/v1/bom/versions/${versionId}/lines/reorder`, {
    body: JSON.stringify({ line_ids: lineIds }),
    method: 'POST',
  });
}

export async function compareBomVersions(leftId: string, rightId: string) {
  return apiRequest<BomCompare>(`${apiBaseUrl}/v1/bom/versions/${leftId}/compare/${rightId}`);
}

export async function fetchBomPreviewHtml(versionId: string, toolbar = true) {
  const searchParams = new URLSearchParams({ toolbar: String(toolbar) });
  const response = await fetch(
    `${apiBaseUrl}/v1/bom/versions/${versionId}/preview?${searchParams.toString()}`,
    {
      credentials: 'include',
      headers: getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : undefined,
    },
  );
  if (!response.ok) throw new Error(response.statusText);
  return response.text();
}

export async function downloadBomFile(versionId: string, format: 'pdf' | 'xlsx') {
  const response = await fetch(`${apiBaseUrl}/v1/bom/versions/${versionId}/export/${format}`, {
    credentials: 'include',
    headers: getAccessToken() ? { Authorization: `Bearer ${getAccessToken()}` } : undefined,
  });
  if (!response.ok) throw new Error(response.statusText);
  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const match = /filename="([^"]+)"/.exec(disposition);
  const filename = match?.[1] ?? `specification.${format}`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
