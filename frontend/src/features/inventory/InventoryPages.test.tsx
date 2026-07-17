import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Outlet, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MainLayout } from '../../layouts/MainLayout';
import { renderWithProviders } from '../../test/render';
import {
  InventoryDocumentsPage,
  ItemCatalogPage,
  StockPage,
  WarehouseDashboardPage,
} from './InventoryPages';

const apiMocks = vi.hoisted(() => ({
  listInventory: vi.fn(),
  lowStock: vi.fn(),
  postDocument: vi.fn(),
}));

const authState = vi.hoisted(() => ({
  permissions: new Set<string>(),
}));

vi.mock('./api', () => ({
  addDocumentLine: vi.fn(),
  cancelDocument: vi.fn(),
  createInventory: vi.fn(),
  deleteInventory: vi.fn(),
  listDocumentLines: vi.fn(),
  listInventory: apiMocks.listInventory,
  lowStock: apiMocks.lowStock,
  postDocument: apiMocks.postDocument,
}));

vi.mock('../organizations/api', () => ({
  listEntities: vi.fn(() =>
    Promise.resolve({
      items: [{ id: 'org-1', name: 'UkrFlyBud' }],
      page: 1,
      page_size: 1,
      total: 1,
    }),
  ),
}));

vi.mock('../identity/AuthContext', () => ({
  useAuth: () => ({
    hasPermission: (permission: string) => authState.permissions.has(permission),
    logout: vi.fn(),
    status: 'ready',
    user: { display_name: 'Admin', is_superuser: false, must_change_password: false },
  }),
}));

const fixtures = {
  categories: [
    {
      id: 'cat-1',
      organization_id: 'org-1',
      code: 'ELEC',
      name: 'Електроніка',
      is_active: true,
      version: 1,
    },
  ],
  documents: [
    {
      id: 'doc-1',
      organization_id: 'org-1',
      document_number: 'INV-1',
      document_type: 'issue',
      status: 'draft',
      document_date: '2026-07-17T10:00:00Z',
      source_warehouse_id: 'wh-1',
      destination_warehouse_id: null,
      version: 1,
    },
  ],
  items: [
    {
      id: 'item-1',
      organization_id: 'org-1',
      sku: 'MOTOR-001',
      name: 'Двигун',
      category_id: 'cat-1',
      unit_of_measure_id: 'unit-1',
      item_type: 'component',
      track_lots: false,
      track_serial_numbers: false,
      minimum_stock: '5',
      is_active: true,
      version: 1,
    },
    {
      id: 'item-2',
      organization_id: 'org-1',
      sku: 'FRAME-001',
      name: 'Рама',
      category_id: 'cat-1',
      unit_of_measure_id: 'unit-1',
      item_type: 'component',
      track_lots: false,
      track_serial_numbers: false,
      minimum_stock: '1',
      is_active: true,
      version: 1,
    },
  ],
  stock: [
    {
      id: 'stock-1',
      organization_id: 'org-1',
      item_id: 'item-1',
      warehouse_id: 'wh-1',
      location_id: null,
      lot_id: null,
      quantity: '2',
      updated_at: '2026-07-17T10:00:00Z',
    },
    {
      id: 'stock-2',
      organization_id: 'org-1',
      item_id: 'item-2',
      warehouse_id: 'wh-1',
      location_id: null,
      lot_id: null,
      quantity: '8',
      updated_at: '2026-07-17T10:00:00Z',
    },
  ],
  units: [
    {
      id: 'unit-1',
      organization_id: 'org-1',
      code: 'PCS',
      name: 'штука',
      symbol: 'шт',
      precision: 0,
      is_active: true,
      version: 1,
    },
  ],
  warehouses: [
    {
      id: 'wh-1',
      organization_id: 'org-1',
      site_id: 'site-1',
      code: 'MAIN',
      name: 'Основний склад',
      warehouse_type: 'main',
      allow_negative_stock: false,
      is_active: true,
      version: 1,
    },
    {
      id: 'wh-2',
      organization_id: 'org-1',
      site_id: 'site-2',
      code: 'OLD',
      name: 'Старий склад',
      warehouse_type: 'main',
      allow_negative_stock: false,
      is_active: false,
      version: 1,
    },
  ],
};

describe('Inventory pages', () => {
  beforeEach(() => {
    apiMocks.postDocument.mockReset();
    apiMocks.lowStock.mockResolvedValue([]);
    apiMocks.listInventory.mockImplementation((kind: string) => {
      const data: Record<string, unknown[]> = {
        categories: fixtures.categories,
        documents: fixtures.documents,
        items: fixtures.items,
        locations: [],
        lots: [],
        serials: [],
        sites: [
          {
            id: 'site-1',
            organization_id: 'org-1',
            code: 'KYIV',
            name: 'Київ',
            is_active: true,
            version: 1,
          },
          {
            id: 'site-2',
            organization_id: 'org-1',
            code: 'OLD',
            name: 'Старий',
            is_active: false,
            version: 1,
          },
        ],
        stock: fixtures.stock,
        units: fixtures.units,
        warehouses: fixtures.warehouses,
      };
      return Promise.resolve({
        items: data[kind] ?? [],
        page: 1,
        page_size: 100,
        total: data[kind]?.length ?? 0,
      });
    });
    authState.permissions = new Set();
  });

  it('hides warehouse navigation when the user lacks permissions', () => {
    renderWithProviders(
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Outlet />} />
        </Route>
      </Routes>,
    );

    expect(screen.queryByRole('link', { name: 'Склад' })).not.toBeInTheDocument();
  });

  it('shows warehouse pages inside one dropdown when the user has permissions', async () => {
    authState.permissions = new Set(['inventory.stock.read', 'inventory.items.read']);

    renderWithProviders(
      <Routes>
        <Route element={<MainLayout />}>
          <Route path="/" element={<Outlet />} />
        </Route>
      </Routes>,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Склад' }));

    expect(screen.getByRole('menuitem', { name: 'Огляд складу' })).toHaveAttribute(
      'href',
      '/warehouse',
    );
    expect(screen.getByRole('menuitem', { name: 'Номенклатура' })).toHaveAttribute(
      'href',
      '/items',
    );
    expect(screen.queryByRole('menuitem', { name: 'Налаштування складу' })).not.toBeInTheDocument();
  });

  it('counts only active sites and warehouses on the dashboard', async () => {
    renderWithProviders(<WarehouseDashboardPage />);

    const sitesCard = (await screen.findByText('Активні майданчики')).closest('div');
    const warehousesCard = screen.getByText('Активні склади').closest('div');

    expect(sitesCard).toHaveTextContent('1');
    expect(warehousesCard).toHaveTextContent('1');
  });

  it('shows item catalog data and empty state when search has no results', async () => {
    apiMocks.listInventory.mockImplementation(
      (kind: string, params: { filters?: Record<string, string> }) => {
        if (kind === 'items' && params?.filters?.search === 'missing') {
          return Promise.resolve({ items: [], page: 1, page_size: 100, total: 0 });
        }
        const data: Record<string, unknown[]> = {
          categories: fixtures.categories,
          items: fixtures.items,
          sites: [],
          stock: [],
          units: fixtures.units,
          warehouses: fixtures.warehouses,
        };
        return Promise.resolve({
          items: data[kind] ?? [],
          page: 1,
          page_size: 100,
          total: data[kind]?.length ?? 0,
        });
      },
    );

    renderWithProviders(<ItemCatalogPage />);

    expect(await screen.findByText('MOTOR-001')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText(/Пошук/), 'missing');
    expect(await screen.findByText('Номенклатуру ще не створено.')).toBeInTheDocument();
  });

  it('filters stock to positions below minimum', async () => {
    renderWithProviders(<StockPage />);

    expect(await screen.findByText('MOTOR-001')).toBeInTheDocument();
    expect(screen.getByText('FRAME-001')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Нижче мінімуму' }));

    expect(screen.getByText('MOTOR-001')).toBeInTheDocument();
    expect(screen.queryByText('FRAME-001')).not.toBeInTheDocument();
  });

  it('shows post confirmation and friendly insufficient stock error', async () => {
    apiMocks.postDocument.mockRejectedValue({ message: 'На складі недостатньо залишку.' });
    renderWithProviders(<InventoryDocumentsPage />);

    await userEvent.click(await screen.findByRole('button', { name: 'Провести' }));
    expect(
      screen.getByText(
        'Після проведення документ змінить складські залишки. Редагування буде недоступне.',
      ),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Провести' }));

    await waitFor(() => expect(apiMocks.postDocument).toHaveBeenCalledWith('doc-1'));
    expect(await screen.findByText('На складі недостатньо залишку.')).toBeInTheDocument();
  });
});
