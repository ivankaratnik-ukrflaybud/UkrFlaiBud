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

export function WarehouseSettingsPage() {
  const [tab, setTab] = useState<SettingTab>('sites');
  const lookups = useInventoryLookups();

  return (
    <Stack spacing={3}>
      <PageHeader subtitle="Довідники, які можна змінювати без коду." title="Налаштування складу" />
      <Paper variant="outlined">
        <Tabs value={tab} variant="scrollable" onChange={(_, value: SettingTab) => setTab(value)}>
          <Tab label="Майданчики" value="sites" />
          <Tab label="Склади" value="warehouses" />
          <Tab label="Місця зберігання" value="locations" />
          <Tab label="Категорії" value="categories" />
          <Tab label="Одиниці виміру" value="units" />
        </Tabs>
      </Paper>
      <SettingsCrud tab={tab} lookups={lookups} />
    </Stack>
  );
}
