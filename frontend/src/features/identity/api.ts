import { apiBaseUrl, apiRequest } from '../../services/apiClient';
import type {
  CreatedUserResponse,
  CreateUserPayload,
  PaginatedResponse,
  Permission,
  Role,
  TokenResponse,
  User,
  UserSession,
} from './types';

const identityBase = `${apiBaseUrl}/v1`;

export async function login(email: string, password: string) {
  return apiRequest<TokenResponse>(`${identityBase}/auth/login`, {
    body: JSON.stringify({ email, password }),
    method: 'POST',
  });
}

export async function refreshSession() {
  return apiRequest<TokenResponse>(`${identityBase}/auth/refresh`, { method: 'POST' });
}

export async function logout() {
  return apiRequest<void>(`${identityBase}/auth/logout`, { method: 'POST' });
}

export async function logoutAll() {
  return apiRequest<void>(`${identityBase}/auth/logout-all`, { method: 'POST' });
}

export async function changePassword(currentPassword: string, newPassword: string) {
  return apiRequest<void>(`${identityBase}/auth/change-password`, {
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    method: 'POST',
  });
}

export async function listOwnSessions() {
  return apiRequest<UserSession[]>(`${identityBase}/auth/sessions`);
}

export async function revokeOwnSession(sessionId: string) {
  return apiRequest<void>(`${identityBase}/auth/sessions/${sessionId}`, { method: 'DELETE' });
}

export async function listUsers(search = '') {
  const params = new URLSearchParams({ page: '1', page_size: '100' });
  if (search) {
    params.set('search', search);
  }
  return apiRequest<PaginatedResponse<User>>(`${identityBase}/users?${params.toString()}`);
}

export async function createUser(payload: CreateUserPayload) {
  return apiRequest<CreatedUserResponse>(`${identityBase}/users`, {
    body: JSON.stringify(payload),
    method: 'POST',
  });
}

export async function setUserRoles(userId: string, roleIds: string[]) {
  return apiRequest<User>(`${identityBase}/users/${userId}/roles`, {
    body: JSON.stringify({ role_ids: roleIds }),
    method: 'PUT',
  });
}

export async function resetUserPassword(userId: string) {
  return apiRequest<{ temporary_password: string }>(`${identityBase}/users/${userId}/reset-password`, {
    method: 'POST',
  });
}

export async function listRoles(search = '') {
  const params = new URLSearchParams({ page: '1', page_size: '100', sort_by: 'name' });
  if (search) {
    params.set('search', search);
  }
  return apiRequest<PaginatedResponse<Role>>(`${identityBase}/roles?${params.toString()}`);
}

export async function createRole(payload: { code: string; description?: string; name: string }) {
  return apiRequest<Role>(`${identityBase}/roles`, {
    body: JSON.stringify({ ...payload, is_active: true }),
    method: 'POST',
  });
}

export async function listPermissions() {
  return apiRequest<Permission[]>(`${identityBase}/permissions`);
}

export async function setRolePermissions(roleId: string, permissionIds: string[]) {
  return apiRequest<Role>(`${identityBase}/roles/${roleId}/permissions`, {
    body: JSON.stringify({ permission_ids: permissionIds }),
    method: 'PUT',
  });
}
