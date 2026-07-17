import { CircularProgress, Stack } from '@mui/material';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from './AuthContext';

export function ProtectedRoute({ permission }: { permission?: string }) {
  const auth = useAuth();
  const location = useLocation();

  if (auth.status === 'loading') {
    return (
      <Stack alignItems="center" sx={{ py: 8 }}>
        <CircularProgress />
      </Stack>
    );
  }

  if (!auth.user) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  if (auth.user.must_change_password && location.pathname !== '/change-password') {
    return <Navigate replace to="/change-password" />;
  }

  if (permission && !auth.hasPermission(permission)) {
    return <Navigate replace to="/access-denied" />;
  }

  return <Outlet />;
}
