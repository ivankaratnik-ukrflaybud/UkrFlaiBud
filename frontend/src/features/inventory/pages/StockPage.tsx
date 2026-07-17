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

export function StockPage() {
  const [warehouseId, setWarehouseId] = useState('');
  const [belowMinimum, setBelowMinimum] = useState(false);
  const lookups = useInventoryLookups();
  const stockQuery = useInventoryList('stock', { warehouse_id: warehouseId });
  const balances = stockQuery.data?.items ?? [];
  const filtered = belowMinimum
    ? balances.filter((balance) => {
        const item = lookups.items.find((candidate) => candidate.id === balance.item_id);
        return item ? Number(balance.quantity) < Number(item.minimum_stock) : false;
      })
    : balances;

  return (
    <Stack spacing={3}>
      <PageHeader subtitle="Фактичні залишки у доступних складах." title="Залишки" />
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <FormControl fullWidth>
            <InputLabel>Склад</InputLabel>
            <Select
              label="Склад"
              value={warehouseId}
              onChange={(event) => setWarehouseId(event.target.value)}
            >
              <MenuItem value="">Усі доступні склади</MenuItem>
              {lookups.warehouses.map((warehouse) => (
                <MenuItem key={warehouse.id} value={warehouse.id}>
                  {warehouse.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            color={belowMinimum ? 'warning' : 'inherit'}
            startIcon={<WarningAmberIcon />}
            variant={belowMinimum ? 'contained' : 'outlined'}
            onClick={() => setBelowMinimum((value) => !value)}
          >
            Нижче мінімуму
          </Button>
        </Stack>
      </Paper>
      <Paper variant="outlined">
        {stockQuery.isLoading || lookups.loading ? (
          <LoadingState />
        ) : (
          <StockTable
            balances={filtered}
            items={lookups.items}
            locations={lookups.locations}
            units={lookups.units}
            warehouses={lookups.warehouses}
          />
        )}
      </Paper>
    </Stack>
  );
}
