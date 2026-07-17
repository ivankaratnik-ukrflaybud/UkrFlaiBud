import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../test/render';
import { SessionsPage } from './SessionsPage';

const revokeMock = vi.fn();

vi.mock('../features/identity/api', () => ({
  listOwnSessions: () =>
    Promise.resolve([
      {
        created_at: '2026-07-16T08:00:00Z',
        device_name: 'Firefox',
        expires_at: '2026-08-15T08:00:00Z',
        id: 'session-1',
        ip_address: '127.0.0.1',
        last_used_at: '2026-07-16T09:00:00Z',
        revoke_reason: null,
        revoked_at: null,
        user_agent: 'Firefox',
      },
    ]),
  revokeOwnSession: (sessionId: string) => revokeMock(sessionId),
}));

describe('SessionsPage', () => {
  beforeEach(() => {
    revokeMock.mockReset();
    revokeMock.mockResolvedValue(undefined);
  });

  it('shows active sessions and lets the user revoke one', async () => {
    renderWithProviders(<SessionsPage />);

    expect(await screen.findByText('Firefox')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Завершити/i }));

    await waitFor(() => expect(revokeMock).toHaveBeenCalledWith('session-1'));
  });
});
