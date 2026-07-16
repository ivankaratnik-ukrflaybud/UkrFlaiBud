import { AppBar, Box, Button, Container, Stack, Toolbar } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, Outlet } from 'react-router-dom';

import { AppLogo } from '../components/AppLogo';

const navItems = [
  { href: '/', labelKey: 'organizations:navigation.dashboard' },
  { href: '/organizations', labelKey: 'organizations:navigation.organizations' },
  { href: '/departments', labelKey: 'organizations:navigation.departments' },
  { href: '/positions', labelKey: 'organizations:navigation.positions' },
  { href: '/employees', labelKey: 'organizations:navigation.employees' },
];

export function MainLayout() {
  const { t } = useTranslation(['organizations']);

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar color="inherit" elevation={0} position="static">
        <Toolbar sx={{ borderBottom: 1, borderColor: 'divider', gap: 3 }}>
          <AppLogo />
          <Stack direction="row" flexWrap="wrap" gap={1}>
            {navItems.map((item) => (
              <Button key={item.href} component={RouterLink} size="small" to={item.href}>
                {t(item.labelKey)}
              </Button>
            ))}
          </Stack>
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: { xs: 3, md: 6 } }}>
        <Outlet />
      </Container>
    </Box>
  );
}
