import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import { AppBar, Box, Button, Container, IconButton, Menu, MenuItem, Stack, Toolbar, Tooltip, Typography } from '@mui/material';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, Outlet, useNavigate } from 'react-router-dom';

import { AppLogo } from '../components/AppLogo';
import { useAuth } from '../features/identity/AuthContext';

const navItems = [
  { href: '/', labelKey: 'organizations:navigation.dashboard' },
  { href: '/organizations', labelKey: 'organizations:navigation.organizations' },
  { href: '/departments', labelKey: 'organizations:navigation.departments' },
  { href: '/positions', labelKey: 'organizations:navigation.positions' },
  { href: '/employees', labelKey: 'organizations:navigation.employees' },
  { href: '/users', labelKey: 'identity:navigation.users', permission: 'users.read' },
  { href: '/roles', labelKey: 'identity:navigation.roles', permission: 'roles.read' },
];

export function MainLayout() {
  const { t } = useTranslation(['identity', 'organizations']);
  const auth = useAuth();
  const navigate = useNavigate();
  const [profileAnchor, setProfileAnchor] = useState<HTMLElement | null>(null);

  const logout = async () => {
    await auth.logout();
    navigate('/login', { replace: true });
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar color="inherit" elevation={0} position="static">
        <Toolbar sx={{ borderBottom: 1, borderColor: 'divider', gap: 3 }}>
          <AppLogo />
          <Stack direction="row" flex={1} flexWrap="wrap" gap={1}>
            {navItems.filter((item) => !item.permission || auth.hasPermission(item.permission)).map((item) => (
              <Button key={item.href} component={RouterLink} size="small" to={item.href}>
                {t(item.labelKey)}
              </Button>
            ))}
          </Stack>
          <Tooltip title={auth.user?.display_name ?? ''}>
            <IconButton color="primary" onClick={(event) => setProfileAnchor(event.currentTarget)}>
              <AccountCircleIcon />
            </IconButton>
          </Tooltip>
          <Menu anchorEl={profileAnchor} open={Boolean(profileAnchor)} onClose={() => setProfileAnchor(null)}>
            <MenuItem disabled>
              <Typography variant="body2">{auth.user?.display_name}</Typography>
            </MenuItem>
            <MenuItem component={RouterLink} to="/sessions" onClick={() => setProfileAnchor(null)}>
              {t('identity:navigation.sessions')}
            </MenuItem>
            <MenuItem onClick={logout}>
              <LogoutIcon fontSize="small" sx={{ mr: 1 }} />
              {t('identity:actions.logout')}
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: { xs: 3, md: 6 } }}>
        <Outlet />
      </Container>
    </Box>
  );
}
