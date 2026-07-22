import { CssBaseline, ThemeProvider } from '@mui/material';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { AuthProvider } from './features/identity/AuthContext';
import { ProtectedRoute } from './features/identity/ProtectedRoute';
import {
  CncDashboardPage,
  CncMachinesPage,
  CncOffcutsPage,
  CncPartsPage,
  CncProgramsPage,
  CncQueuePage,
  CncSettingsPage,
  CncSheetsPage,
  CncToolsPage,
  CncWorkOrdersPage,
} from './features/cnc/CncPages';
import { MainLayout } from './layouts/MainLayout';
import { AccessDeniedPage } from './pages/AccessDeniedPage';
import { BomEditorPage } from './pages/BomEditorPage';
import { BomListPage } from './pages/BomListPage';
import { BomPrintPage } from './pages/BomPrintPage';
import { BomVersionsPage } from './pages/BomVersionsPage';
import { ChangePasswordPage } from './pages/ChangePasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { InventoryDocumentsPage } from './pages/InventoryDocumentsPage';
import { ItemCatalogPage } from './pages/ItemCatalogPage';
import { LoginPage } from './pages/LoginPage';
import { OrganizationsPage } from './pages/OrganizationsPage';
import { PositionsPage } from './pages/PositionsPage';
import { ProductionDashboardPage } from './pages/ProductionDashboardPage';
import { RolesPage } from './pages/RolesPage';
import { SessionsPage } from './pages/SessionsPage';
import { StockPage } from './pages/StockPage';
import { TrackingPage } from './pages/TrackingPage';
import { TransfersPage } from './pages/TransfersPage';
import { UsersPage } from './pages/UsersPage';
import { WarehouseDashboardPage } from './pages/WarehouseDashboardPage';
import { WarehouseSettingsPage } from './pages/WarehouseSettingsPage';
import { queryClient } from './services/queryClient';
import { theme } from './theme/theme';

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<ProtectedRoute />}>
                <Route element={<MainLayout />}>
                  <Route path="/change-password" element={<ChangePasswordPage />} />
                  <Route path="/access-denied" element={<AccessDeniedPage />} />
                  <Route path="/" element={<DashboardPage />} />
                  <Route element={<ProtectedRoute permission="organizations.read" />}>
                    <Route path="/organizations" element={<OrganizationsPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="departments.read" />}>
                    <Route path="/departments" element={<DepartmentsPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="positions.read" />}>
                    <Route path="/positions" element={<PositionsPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="employees.read" />}>
                    <Route path="/employees" element={<EmployeesPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="users.read" />}>
                    <Route path="/users" element={<UsersPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="roles.read" />}>
                    <Route path="/roles" element={<RolesPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="inventory.stock.read" />}>
                    <Route path="/warehouse" element={<WarehouseDashboardPage />} />
                    <Route path="/stock" element={<StockPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="inventory.items.read" />}>
                    <Route path="/items" element={<ItemCatalogPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="inventory.documents.read" />}>
                    <Route path="/inventory-documents" element={<InventoryDocumentsPage />} />
                    <Route path="/transfers" element={<TransfersPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="inventory.tracking.read" />}>
                    <Route path="/tracking" element={<TrackingPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="inventory.warehouses.manage" />}>
                    <Route path="/warehouse-settings" element={<WarehouseSettingsPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="bom.read" />}>
                    <Route path="/specifications" element={<BomListPage />} />
                    <Route path="/specifications/:specificationId" element={<BomEditorPage />} />
                    <Route
                      path="/specifications/:specificationId/versions"
                      element={<BomVersionsPage />}
                    />
                    <Route path="/specifications/:specificationId/print" element={<BomPrintPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="production.read" />}>
                    <Route path="/production" element={<ProductionDashboardPage />} />
                    <Route path="/production/orders" element={<ProductionDashboardPage />} />
                    <Route path="/production/materials" element={<ProductionDashboardPage />} />
                    <Route path="/production/stages" element={<ProductionDashboardPage />} />
                    <Route path="/production/completions" element={<ProductionDashboardPage />} />
                    <Route path="/production/settings" element={<ProductionDashboardPage />} />
                  </Route>
                  <Route element={<ProtectedRoute permission="cnc.read" />}>
                    <Route path="/cnc" element={<CncDashboardPage />} />
                    <Route path="/cnc/queue" element={<CncQueuePage />} />
                    <Route path="/cnc/work-orders" element={<CncWorkOrdersPage />} />
                    <Route path="/cnc/sheet-plans" element={<CncSheetsPage />} />
                    <Route path="/cnc/parts" element={<CncPartsPage />} />
                    <Route path="/cnc/programs" element={<CncProgramsPage />} />
                    <Route path="/cnc/machines" element={<CncMachinesPage />} />
                    <Route path="/cnc/tools" element={<CncToolsPage />} />
                    <Route path="/cnc/offcuts" element={<CncOffcutsPage />} />
                    <Route path="/cnc/settings" element={<CncSettingsPage />} />
                  </Route>
                  <Route path="/sessions" element={<SessionsPage />} />
                </Route>
              </Route>
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
