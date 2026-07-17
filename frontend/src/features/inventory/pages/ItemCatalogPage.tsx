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

export function ItemCatalogPage() {
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const lookups = useInventoryLookups();
  const itemsQuery = useInventoryList('items', { search });
  const stockQuery = useInventoryList('stock');
  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createInventory('items', payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['inventory', 'items'] });
      setDialogOpen(false);
    },
  });

  const stockByItem = useMemo(
    () => totalsByItem(stockQuery.data?.items ?? []),
    [stockQuery.data?.items],
  );

  return (
    <Stack spacing={3}>
      <PageHeader
        action={
          <Button startIcon={<AddIcon />} variant="contained" onClick={() => setDialogOpen(true)}>
            Створити позицію
          </Button>
        }
        subtitle="Каталог матеріалів, комплектуючих, інструментів і готових виробів."
        title="Номенклатура"
      />
      <Paper variant="outlined" sx={{ p: 2 }}>
        <TextField
          fullWidth
          label="Пошук за кодом, назвою або штрихкодом"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </Paper>
      <Paper variant="outlined">
        {itemsQuery.isLoading || lookups.loading ? (
          <LoadingState />
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Код</TableCell>
                  <TableCell>Назва</TableCell>
                  <TableCell>Категорія</TableCell>
                  <TableCell>Тип</TableCell>
                  <TableCell>Одиниця</TableCell>
                  <TableCell>Загальний залишок</TableCell>
                  <TableCell>Мінімальний залишок</TableCell>
                  <TableCell>Стан</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(itemsQuery.data?.items ?? []).length === 0 ? (
                  <EmptyTable colSpan={8} text="Номенклатуру ще не створено." />
                ) : (
                  (itemsQuery.data?.items ?? []).map((item) => (
                    <TableRow hover key={item.id}>
                      <TableCell>{item.sku}</TableCell>
                      <TableCell>{item.name}</TableCell>
                      <TableCell>{nameById(lookups.categories, item.category_id)}</TableCell>
                      <TableCell>{itemTypeLabel(item.item_type)}</TableCell>
                      <TableCell>{unitSymbol(lookups.units, item.unit_of_measure_id)}</TableCell>
                      <TableCell>{formatQuantity(stockByItem[item.id] ?? 0)}</TableCell>
                      <TableCell>{formatQuantity(item.minimum_stock)}</TableCell>
                      <TableCell>
                        <StateChip active={item.is_active} />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
      <ItemDialog
        categories={lookups.categories}
        error={createMutation.error as ApiError | null}
        loading={createMutation.isPending}
        open={dialogOpen}
        organizationId={lookups.organizationId}
        units={lookups.units}
        warehouses={lookups.warehouses}
        onClose={() => setDialogOpen(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
      />
    </Stack>
  );
}
