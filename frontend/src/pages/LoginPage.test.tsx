import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../test/render';
import { LoginPage } from './LoginPage';

const loginMock = vi.fn();

vi.mock('../features/identity/AuthContext', () => ({
  useAuth: () => ({
    login: loginMock,
    status: 'ready',
    user: null,
  }),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it('shows a friendly error after a failed login', async () => {
    loginMock.mockRejectedValueOnce({ message: 'Невірна пошта або пароль.' });
    renderWithProviders(<LoginPage />, ['/login']);

    await userEvent.type(screen.getByLabelText(/Електронна пошта/i), 'bad@example.com');
    await userEvent.type(screen.getByLabelText(/Пароль/i), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: /Увійти/i }));

    expect(await screen.findByText('Невірна пошта або пароль.')).toBeInTheDocument();
    expect(loginMock).toHaveBeenCalledWith('bad@example.com', 'wrong');
  });
});
