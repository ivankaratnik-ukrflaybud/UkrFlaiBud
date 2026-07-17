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

export function TrackingPage() {
  const lookups = useInventoryLookups();
  const lotsQuery = useInventoryList('lots');
  const serialsQuery = useInventoryList('serials');

  return (
    <Stack spacing={3}>
      <PageHeader
        subtitle="Партії та серійні номери для контрольованих позицій."
        title="Партії та серійні номери"
      />
      <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography fontWeight={800} gutterBottom>
            Партії
          </Typography>
          {(lotsQuery.data?.items ?? []).length === 0 ? (
            <EmptyState text="Партії ще не зареєстровано." />
          ) : (
            <Stack spacing={1}>
              {(lotsQuery.data?.items ?? []).map((lot) => (
                <Chip
                  key={lot.id}
                  label={`${nameById(lookups.items, lot.item_id)} · ${lot.lot_number}`}
                />
              ))}
            </Stack>
          )}
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography fontWeight={800} gutterBottom>
            Серійні номери
          </Typography>
          {(serialsQuery.data?.items ?? []).length === 0 ? (
            <EmptyState text="Серійні номери ще не зареєстровано." />
          ) : (
            <Stack spacing={1}>
              {(serialsQuery.data?.items ?? []).map((serial) => (
                <Chip
                  key={serial.id}
                  label={`${nameById(lookups.items, serial.item_id)} · ${serial.serial_number} · ${serial.status}`}
                />
              ))}
            </Stack>
          )}
        </Paper>
      </Box>
    </Stack>
  );
}
