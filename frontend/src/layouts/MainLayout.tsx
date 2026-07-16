import { AppBar, Box, Container, Toolbar } from '@mui/material';
import { Outlet } from 'react-router-dom';

import { AppLogo } from '../components/AppLogo';

export function MainLayout() {
  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar color="inherit" elevation={0} position="static">
        <Toolbar sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <AppLogo />
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: { xs: 3, md: 6 } }}>
        <Outlet />
      </Container>
    </Box>
  );
}

