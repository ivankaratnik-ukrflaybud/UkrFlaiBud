/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { setAccessToken } from '../../services/apiClient';
import * as identityApi from './api';
import type { User } from './types';

interface AuthContextValue {
  accessToken: string | null;
  hasPermission: (permission: string) => boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  status: 'loading' | 'ready';
  updatePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  user: User | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<'loading' | 'ready'>('loading');
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const applySession = useCallback((nextToken: string | null, nextUser: User | null) => {
    setAccessToken(nextToken);
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  const refresh = useCallback(async () => {
    const session = await identityApi.refreshSession();
    applySession(session.access_token, session.user);
  }, [applySession]);

  useEffect(() => {
    let mounted = true;
    identityApi
      .refreshSession()
      .then((session) => {
        if (mounted) {
          applySession(session.access_token, session.user);
        }
      })
      .catch(() => {
        if (mounted) {
          applySession(null, null);
        }
      })
      .finally(() => {
        if (mounted) {
          setStatus('ready');
        }
      });
    return () => {
      mounted = false;
    };
  }, [applySession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken: token,
      hasPermission: (permission: string) => {
        if (user?.is_superuser) {
          return true;
        }
        return permissionsFromToken(token).includes(permission);
      },
      login: async (email: string, password: string) => {
        const session = await identityApi.login(email, password);
        applySession(session.access_token, session.user);
        return session.user;
      },
      logout: async () => {
        try {
          await identityApi.logout();
        } finally {
          applySession(null, null);
        }
      },
      refresh,
      status,
      updatePassword: async (currentPassword: string, newPassword: string) => {
        await identityApi.changePassword(currentPassword, newPassword);
        setUser((current) =>
          current ? { ...current, must_change_password: false, version: current.version + 1 } : current,
        );
      },
      user,
    }),
    [applySession, refresh, status, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }
  return value;
}

function permissionsFromToken(token: string | null) {
  if (!token) {
    return [];
  }
  try {
    const payload = JSON.parse(atob(token.split('.')[1])) as { permissions?: string[] };
    return payload.permissions ?? [];
  } catch {
    return [];
  }
}
