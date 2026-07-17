import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/render';
import { ProtectedRoute } from './ProtectedRoute';

const authState = vi.hoisted(() => ({
  value: {
    hasPermission: () => false,
    status: 'ready',
    user: null as null | { must_change_password: boolean },
  },
}));

vi.mock('./AuthContext', () => ({
  useAuth: () => authState.value,
}));

describe('ProtectedRoute', () => {
  beforeEach(() => {
    authState.value = {
      hasPermission: () => false,
      status: 'ready',
      user: null,
    };
  });

  it('redirects anonymous users to login', () => {
    renderWithProviders(
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<div>Protected</div>} />
        </Route>
        <Route path="/login" element={<div>Login screen</div>} />
      </Routes>,
    );

    expect(screen.getByText('Login screen')).toBeInTheDocument();
  });

  it('redirects signed-in users without permission to access denied', () => {
    authState.value = {
      hasPermission: () => false,
      status: 'ready',
      user: { must_change_password: false },
    };

    renderWithProviders(
      <Routes>
        <Route element={<ProtectedRoute permission="users.read" />}>
          <Route path="/" element={<div>Users</div>} />
        </Route>
        <Route path="/access-denied" element={<div>Access denied</div>} />
      </Routes>,
    );

    expect(screen.getByText('Access denied')).toBeInTheDocument();
  });
});
