/* eslint-disable @typescript-eslint/no-unused-vars */
import AddIcon from '@mui/icons-material/Add';
import InventoryIcon from '@mui/icons-material/Inventory';
import MoveDownIcon from '@mui/icons-material/MoveDown';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useMemo, useState } from 'react';

import { listEntities } from '../../organizations/api';
import {
  addDocumentLine,
  cancelDocument,
  createInventory,
  deleteInventory,
  listInventory,
  lowStock,
  postDocument,
} from '../api';
import type {
  Category,
  InventoryDocument,
  Item,
  Location,
  Site,
  StockBalance,
  Unit,
  Warehouse,
} from '../types';
import { queryClient } from '../../../services/queryClient';
import type { ApiError } from '../../../services/apiClient';

import {
  DocumentCreateDialog,
  DocumentTable,
  EmptyState,
  EmptyTable,
  FriendlyError,
  ItemDialog,
  LoadingState,
  MetricCard,
  PageHeader,
  SettingsCrud,
  StateChip,
  StockTable,
  TransferPanel,
  formatQuantity,
  itemTypeLabel,
  nameById,
  totalsByItem,
  unitSymbol,
  useInventoryList,
  useInventoryLookups,
} from './shared';
import type { SettingTab } from './shared';

export function WarehouseDashboardPage() {
  const lookups = useInventoryLookups();
  const itemsQuery = useInventoryList('items');
  const documentsQuery = useInventoryList('documents');
  const stockQuery = useInventoryList('stock');
  const organizationId =
    lookups.sites[0]?.organization_id ?? lookups.warehouses[0]?.organization_id;
  const lowStockQuery = useQuery({
    enabled: Boolean(organizationId),
    queryKey: ['inventory', 'low-stock', organizationId],
    queryFn: () => lowStock(organizationId ?? ''),
  });

  if (lookups.loading || itemsQuery.isLoading || documentsQuery.isLoading || stockQuery.isLoading) {
    return <LoadingState />;
  }

  const today = new Date().toISOString().slice(0, 10);
  const activeItems = (itemsQuery.data?.items ?? []).filter((item) => item.is_active);
  const activeSites = lookups.sites.filter((site) => site.is_active);
  const activeWarehouses = lookups.warehouses.filter((warehouse) => warehouse.is_active);
  const documents = documentsQuery.data?.items ?? [];
  const stock = stockQuery.data?.items ?? [];
  const postedToday = documents.filter(
    (document) => document.status === 'posted' && document.document_date.slice(0, 10) === today,
  ).length;

  return (
    <Stack spacing={3}>
      <PageHeader
        subtitle="Швидкий стан складів, документів і номенклатури."
        title="Огляд складу"
      />
      <Box
        sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: 'repeat(6, 1fr)' } }}
      >
        <MetricCard label="Активні майданчики" value={activeSites.length} />
        <MetricCard label="Номенклатурні позиції" value={activeItems.length} />
        <MetricCard label="Нижче мінімуму" value={lowStockQuery.data?.length ?? 0} tone="warning" />
        <MetricCard
          label="Чернетки"
          value={documents.filter((document) => document.status === 'draft').length}
        />
        <MetricCard label="Проведено сьогодні" value={postedToday} />
        <MetricCard label="Активні склади" value={activeWarehouses.length} />
      </Box>

      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1.2fr 0.8fr' } }}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography fontWeight={800} gutterBottom>
            Останні складські документи
          </Typography>
          <DocumentTable
            documents={documents.slice(0, 6)}
            warehouses={lookups.warehouses}
            compact
          />
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography fontWeight={800} gutterBottom>
            Низькі залишки
          </Typography>
          {(lowStockQuery.data ?? []).length === 0 ? (
            <EmptyState text="Немає позицій нижче мінімального залишку." />
          ) : (
            <Stack spacing={1}>
              {(lowStockQuery.data ?? []).slice(0, 6).map((row) => (
                <Alert icon={<WarningAmberIcon />} key={row.item_id} severity="warning">
                  {row.sku} · {row.name}: {formatQuantity(row.quantity)} / мін.{' '}
                  {formatQuantity(row.minimum_stock)}
                </Alert>
              ))}
            </Stack>
          )}
        </Paper>
      </Box>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography fontWeight={800} gutterBottom>
          Залишки за складами
        </Typography>
        <Stack direction="row" flexWrap="wrap" gap={1}>
          {activeWarehouses.map((warehouse) => {
            const quantity = stock
              .filter((balance) => balance.warehouse_id === warehouse.id)
              .reduce((sum, balance) => sum + Number(balance.quantity), 0);
            return (
              <Chip key={warehouse.id} label={`${warehouse.name}: ${formatQuantity(quantity)}`} />
            );
          })}
        </Stack>
      </Paper>
    </Stack>
  );
}
