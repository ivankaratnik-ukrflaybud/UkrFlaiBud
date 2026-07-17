export interface User {
  id: string;
  employee_id: string | null;
  email: string;
  display_name: string;
  is_active: boolean;
  is_superuser: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  failed_login_attempts: number;
  locked_until: string | null;
  version: number;
}

export interface Role {
  id: string;
  name: string;
  code: string;
  description: string | null;
  is_system: boolean;
  is_active: boolean;
  version: number;
}

export interface Permission {
  id: string;
  code: string;
  name: string;
  description: string | null;
  module: string;
  is_active: boolean;
}

export interface UserSession {
  id: string;
  device_name: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_used_at: string;
  expires_at: string;
  revoked_at: string | null;
  revoke_reason: string | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface CreateUserPayload {
  email: string;
  display_name: string;
  employee_id?: string | null;
  temporary_password?: string | null;
  is_active: boolean;
  is_superuser: boolean;
  role_ids: string[];
}

export interface CreatedUserResponse {
  user: User;
  temporary_password: string | null;
}
