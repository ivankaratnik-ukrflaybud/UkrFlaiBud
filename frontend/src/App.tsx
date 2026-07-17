import { CssBaseline, ThemeProvider } from '@mui/material';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { AuthProvider } from './features/identity/AuthContext';
import { ProtectedRoute } from './features/identity/ProtectedRoute';
import { MainLayout } from './layouts/MainLayout';
import { AccessDeniedPage } from './pages/AccessDeniedPage';
import { ChangePasswordPage } from './pages/ChangePasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { DepartmentsPage } from './pages/DepartmentsPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { LoginPage } from './pages/LoginPage';
import { OrganizationsPage } from './pages/OrganizationsPage';
import { PositionsPage } from './pages/PositionsPage';
import { RolesPage } from './pages/RolesPage';
import { SessionsPage } from './pages/SessionsPage';
import { UsersPage } from './pages/UsersPage';
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
