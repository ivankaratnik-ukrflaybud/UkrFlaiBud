import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Outlet, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MainLayout } from '../../layouts/MainLayout';
import { renderWithProviders } from '../../test/render';
import { CncWorkOrdersPage } from './CncPages';

const apiMocks = vi.hoisted(() => ({
  cncAction: vi.fn(),
  fetchCncDashboard: vi.fn(),
  fetchReadiness: vi.fn(),
  issueCncMaterial: vi.fn(),
  listCncQueue: vi.fn(),
  listCncWorkOrders: vi.fn(),
  reportCncOutput: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  permissions: new Set<string>(),
}));

vi.mock('./api', () => ({
  cncAction: apiMocks.cncAction,
  downloadCncWorkOrder: vi.fn(),
  fetchCncDashboard: apiMocks.fetchCncDashboard,
  fetchReadiness: apiMocks.fetchReadiness,
  issueCncMaterial: apiMocks.issueCncMaterial,
  listCncMachines: vi.fn(() => Promise.resolve({ items: [], page: 1, page_size: 100, total: 0 })),
  listCncParts: vi.fn(() => Promise.resolve({ items: [], page: 1, page_size: 100, total: 0 })),
  listCncPrograms: vi.fn(() => Promise.resolve({ items: [], page: 1, page_size: 100, total: 0 })),
  listCncQueue: apiMocks.listCncQueue,
  listCncSheetPlans: vi.fn(() => Promise.resolve({ items: [], page: 1, page_size: 100, total: 0 })),
  listCncWorkOrders: apiMocks.listCncWorkOrders,
  reportCncOutput: apiMocks.reportCncOutput,
}));

vi.mock('../identity/AuthContext', () => ({
  useAuth: () => ({
    hasPermission: (permission: string) => authState.permissions.has(permission),
    logout: vi.fn(),
    status: 'ready',
    user: {
      display_name: 'Admin',
      is_superuser: false,
      must_change_password: false,
      organization_id: 'org-1',
    },
  }),
}));

describe('CNC pages', () => {
  beforeEach(() => {
    authState.permissions = new Set(['cnc.read', 'cnc.machines.read', 'cnc.programs.read', 'cnc.tools.read']);
    apiMocks.fetchCncDashboard.mockResolvedValue({
      available_machines: 1,
      blocked_work_orders: 0,
      completed_today: 1,
      overdue_work_orders: 0,
      queued_work_orders: 1,
      rejected_today: '0',
      running_machines: 1,
      running_work_orders: 1,
    });
    apiMocks.listCncWorkOrders.mockResolvedValue({
      items: [
        {
          id: 'wo-1',
          completed_quantity: '1',
          name: 'Завдання',
          part_name_snapshot: 'Панель',
          planned_quantity: '5',
          priority: 'normal',
          rejected_quantity: '0',
          status: 'running',
          work_order_number: 'CNC-001',
        },
      ],
      page: 1,
      page_size: 100,
      total: 1,
    });
    apiMocks.listCncQueue.mockResolvedValue({ items: [], page: 1, page_size: 100, total: 0 });
    apiMocks.fetchReadiness.mockResolvedValue({
      checklist: [
        { code: 'machine', label: 'Верстат готовий', ready: true },
        { code: 'program', label: 'Програма готова', ready: true },
      ],
      ready: true,
      work_order_id: 'wo-1',
    });
    apiMocks.cncAction.mockResolvedValue({});
    apiMocks.issueCncMaterial.mockResolvedValue({});
    apiMocks.reportCncOutput.mockResolvedValue({});
  });

  it('shows CNC dropdown without overcrowding navigation', async () => {
    renderWithProviders(
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Outlet />} />
        </Route>
      </Routes>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'ЧПК' }));

    expect(screen.getByRole('menuitem', { name: 'Огляд ЧПК' })).toHaveAttribute('href', '/cnc');
    expect(screen.getByRole('menuitem', { name: 'Верстати' })).toHaveAttribute('href', '/cnc/machines');
  });

  it('renders operator screen actions and reports quantities', async () => {
    renderWithProviders(<CncWorkOrdersPage />);

    expect(await screen.findAllByText('CNC-001')).toHaveLength(2);
    await userEvent.click(screen.getByRole('button', { name: 'Пауза' }));
    await userEvent.click(screen.getByRole('button', { name: 'Повідомити кількість' }));

    expect(apiMocks.cncAction).toHaveBeenCalledWith('wo-1', 'pause', 'Пауза оператора');
    expect(apiMocks.reportCncOutput).toHaveBeenCalledWith('wo-1', '1', '0');
  });
});
