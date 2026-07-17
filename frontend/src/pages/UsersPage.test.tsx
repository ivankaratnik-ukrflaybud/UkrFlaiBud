import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../test/render';
import { UsersPage } from './UsersPage';

const createUserMock = vi.fn();

vi.mock('../features/identity/api', () => ({
  createUser: (payload: unknown) => createUserMock(payload),
  listRoles: () =>
    Promise.resolve({
      items: [{ id: 'role-1', name: 'Працівник', code: 'employee', description: null, is_active: true, is_system: true, version: 1 }],
      page: 1,
      page_size: 100,
      total: 1,
    }),
  listUsers: () => Promise.resolve({ items: [], page: 1, page_size: 100, total: 0 }),
  resetUserPassword: () => Promise.resolve({ temporary_password: 'TempPass123!' }),
}));

describe('UsersPage', () => {
  beforeEach(() => {
    createUserMock.mockReset();
    createUserMock.mockResolvedValue({
      temporary_password: 'TempPass123!',
      user: {
        display_name: 'Новий користувач',
        email: 'new@example.com',
        failed_login_attempts: 0,
        employee_id: null,
        id: 'user-1',
        is_active: true,
        is_superuser: false,
        last_login_at: null,
        locked_until: null,
        must_change_password: true,
        version: 1,
      },
    });
  });

  it('creates a user through the wizard with role selection', async () => {
    renderWithProviders(<UsersPage />);

    await userEvent.click(screen.getByRole('button', { name: /Створити користувача/i }));
    await userEvent.type(screen.getByLabelText(/Ім'я/i), 'Новий користувач');
    await userEvent.type(screen.getByLabelText(/Електронна пошта/i), 'new@example.com');
    await userEvent.click(screen.getByRole('button', { name: /Далі/i }));
    await userEvent.click(screen.getByLabelText(/Ролі/i));
    await userEvent.click(await screen.findByRole('option', { name: /Працівник/i }));
    await userEvent.keyboard('{Escape}');
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: /^Створити$/i }));

    await waitFor(() =>
      expect(createUserMock).toHaveBeenCalledWith(
        expect.objectContaining({
          display_name: 'Новий користувач',
          email: 'new@example.com',
          role_ids: ['role-1'],
        }),
      ),
    );
  });
});
