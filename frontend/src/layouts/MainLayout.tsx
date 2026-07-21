import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import LogoutIcon from '@mui/icons-material/Logout';
import {
  AppBar,
  Box,
  Button,
  Container,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, Outlet, useNavigate } from 'react-router-dom';

import { AppLogo } from '../components/AppLogo';
import { useAuth } from '../features/identity/AuthContext';

const navItems: Array<{ href: string; label?: string; labelKey?: string; permission?: string }> = [
  { href: '/', labelKey: 'organizations:navigation.dashboard' },
  { href: '/organizations', labelKey: 'organizations:navigation.organizations' },
  { href: '/departments', labelKey: 'organizations:navigation.departments' },
  { href: '/positions', labelKey: 'organizations:navigation.positions' },
  { href: '/employees', labelKey: 'organizations:navigation.employees' },
  { href: '/users', labelKey: 'identity:navigation.users', permission: 'users.read' },
  { href: '/roles', labelKey: 'identity:navigation.roles', permission: 'roles.read' },
];

const warehouseNavItems = [
  { href: '/warehouse', label: 'Огляд складу', permission: 'inventory.stock.read' },
  { href: '/items', label: 'Номенклатура', permission: 'inventory.items.read' },
  { href: '/stock', label: 'Залишки', permission: 'inventory.stock.read' },
  {
    href: '/inventory-documents',
    label: 'Складські документи',
    permission: 'inventory.documents.read',
  },
  { href: '/transfers', label: 'Переміщення', permission: 'inventory.documents.read' },
  { href: '/tracking', label: 'Партії та серійні номери', permission: 'inventory.tracking.read' },
  {
    href: '/warehouse-settings',
    label: 'Налаштування складу',
    permission: 'inventory.warehouses.manage',
  },
];

const bomNavItems = [
  { href: '/specifications', label: 'Специфікації', permission: 'bom.read' },
];

const productionNavItems = [
  { href: '/production', label: 'Огляд виробництва', permission: 'production.read' },
  { href: '/production/orders', label: 'Виробничі замовлення', permission: 'production.read' },
  { href: '/production/materials', label: 'Матеріали до виробництва', permission: 'production.read' },
  { href: '/production/stages', label: 'Етапи виробництва', permission: 'production.read' },
  { href: '/production/completions', label: 'Готова продукція', permission: 'production.read' },
  {
    href: '/production/settings',
    label: 'Налаштування виробництва',
    permission: 'production.settings',
  },
];

export function MainLayout() {
  const { t } = useTranslation(['identity', 'organizations']);
  const auth = useAuth();
  const navigate = useNavigate();
  const [profileAnchor, setProfileAnchor] = useState<HTMLElement | null>(null);
  const [warehouseAnchor, setWarehouseAnchor] = useState<HTMLElement | null>(null);
  const [productionAnchor, setProductionAnchor] = useState<HTMLElement | null>(null);
  const visibleWarehouseItems = warehouseNavItems.filter((item) =>
    auth.hasPermission(item.permission),
  );
  const visibleBomItems = bomNavItems.filter((item) => auth.hasPermission(item.permission));
  const visibleProductionItems = productionNavItems.filter((item) =>
    auth.hasPermission(item.permission),
  );

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
            {navItems
              .filter((item) => !item.permission || auth.hasPermission(item.permission))
              .map((item) => (
                <Button key={item.href} component={RouterLink} size="small" to={item.href}>
                  {item.label ?? t(item.labelKey ?? '')}
                </Button>
              ))}
            {visibleWarehouseItems.length > 0 ? (
              <>
                <Button size="small" onClick={(event) => setWarehouseAnchor(event.currentTarget)}>
                  Склад
                </Button>
                <Menu
                  anchorEl={warehouseAnchor}
                  open={Boolean(warehouseAnchor)}
                  onClose={() => setWarehouseAnchor(null)}
                >
                  {visibleWarehouseItems.map((item) => (
                    <MenuItem
                      component={RouterLink}
                      key={item.href}
                      onClick={() => setWarehouseAnchor(null)}
                      to={item.href}
                    >
                      {item.label}
                    </MenuItem>
                  ))}
                </Menu>
              </>
            ) : null}
            {visibleBomItems.map((item) => (
              <Button key={item.href} component={RouterLink} size="small" to={item.href}>
                {item.label}
              </Button>
            ))}
            {visibleProductionItems.length > 0 ? (
              <>
                <Button size="small" onClick={(event) => setProductionAnchor(event.currentTarget)}>
                  Виробництво
                </Button>
                <Menu
                  anchorEl={productionAnchor}
                  open={Boolean(productionAnchor)}
                  onClose={() => setProductionAnchor(null)}
                >
                  {visibleProductionItems.map((item) => (
                    <MenuItem
                      component={RouterLink}
                      key={item.href}
                      onClick={() => setProductionAnchor(null)}
                      to={item.href}
                    >
                      {item.label}
                    </MenuItem>
                  ))}
                </Menu>
              </>
            ) : null}
          </Stack>
          <Tooltip title={auth.user?.display_name ?? ''}>
            <IconButton color="primary" onClick={(event) => setProfileAnchor(event.currentTarget)}>
              <AccountCircleIcon />
            </IconButton>
          </Tooltip>
          <Menu
            anchorEl={profileAnchor}
            open={Boolean(profileAnchor)}
            onClose={() => setProfileAnchor(null)}
          >
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
