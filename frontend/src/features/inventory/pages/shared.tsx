/* eslint-disable react-refresh/only-export-components */
import AddIcon from '@mui/icons-material/Add';
import InventoryIcon from '@mui/icons-material/Inventory';
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Toolbar,
  Typography,
} from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useState } from 'react';

import { listEntities } from '../../organizations/api';
import {
  addDocumentLine,
  createInventory,
  deleteInventory,
  listInventory,
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

export type SettingTab = 'sites' | 'warehouses' | 'locations' | 'categories' | 'units';

export const documentTypeLabels: Record<string, string> = {
  receipt: 'Оприбуткування',
  issue: 'Видача',
  transfer: 'Переміщення',
  adjustment_in: 'Коригування плюс',
  adjustment_out: 'Коригування мінус',
  return_in: 'Повернення на склад',
  return_out: 'Повернення зі складу',
};

export const statusLabels: Record<string, string> = {
  draft: 'Чернетка',
  posted: 'Проведено',
  cancelled: 'Скасовано',
};

export function TransferPanel() {
  const lookups = useInventoryLookups();
  return (
    <DocumentCreateDialog
      fixedType="transfer"
      items={lookups.items}
      open
      organizationId={lookups.organizationId}
      units={lookups.units}
      warehouses={lookups.warehouses}
      embedded
      onClose={() => undefined}
    />
  );
}

export function SettingsCrud({
  lookups,
  tab,
}: {
  lookups: ReturnType<typeof useInventoryLookups>;
  tab: SettingTab;
}) {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const createMutation = useMutation({
    mutationFn: () => {
      const organization_id = lookups.organizationId;
      if (!organization_id) {
        throw new Error('Спочатку створіть організацію або майданчик.');
      }
      if (tab === 'warehouses') {
        return createInventory(tab, {
          organization_id,
          site_id: lookups.sites[0]?.id,
          code,
          name,
          warehouse_type: 'main',
        });
      }
      if (tab === 'locations') {
        return createInventory(tab, {
          organization_id,
          warehouse_id: lookups.warehouses[0]?.id,
          code,
          name,
          location_type: 'bin',
        });
      }
      if (tab === 'units') {
        return createInventory(tab, {
          organization_id,
          code,
          name,
          symbol: code.toLowerCase(),
          precision: 0,
        });
      }
      return createInventory(tab, { organization_id, code, name });
    },
    onSuccess: async () => {
      setName('');
      setCode('');
      await queryClient.invalidateQueries({ queryKey: ['inventory'] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteInventory(tab, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['inventory'] }),
  });
  const rows = lookups[tab] as Array<Site | Warehouse | Location | Category | Unit>;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={2}>
        <Box
          sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 2fr auto' } }}
        >
          <TextField label="Код" value={code} onChange={(event) => setCode(event.target.value)} />
          <TextField label="Назва" value={name} onChange={(event) => setName(event.target.value)} />
          <Button
            disabled={!code.trim() || !name.trim() || createMutation.isPending}
            startIcon={<AddIcon />}
            variant="contained"
            onClick={() => createMutation.mutate()}
          >
            Додати
          </Button>
        </Box>
        {createMutation.error ? <FriendlyError error={createMutation.error as ApiError} /> : null}
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Код</TableCell>
                <TableCell>Назва</TableCell>
                <TableCell>Стан</TableCell>
                <TableCell align="right">Дії</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <EmptyTable colSpan={4} text="Записів ще немає." />
              ) : (
                rows.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.code}</TableCell>
                    <TableCell>{row.name}</TableCell>
                    <TableCell>
                      <StateChip active={row.is_active} />
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        color="warning"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(row.id)}
                      >
                        Деактивувати
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Stack>
    </Paper>
  );
}

export function DocumentCreateDialog({
  embedded = false,
  fixedType,
  items,
  onClose,
  open,
  organizationId,
  units,
  warehouses,
}: {
  embedded?: boolean;
  fixedType?: string;
  items: Item[];
  onClose: () => void;
  open: boolean;
  organizationId?: string;
  units: Unit[];
  warehouses: Warehouse[];
}) {
  const [documentType, setDocumentType] = useState(fixedType ?? 'receipt');
  const [sourceWarehouseId, setSourceWarehouseId] = useState('');
  const [destinationWarehouseId, setDestinationWarehouseId] = useState('');
  const [itemId, setItemId] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [postAfterSave, setPostAfterSave] = useState(false);
  const mutation = useMutation({
    mutationFn: async () => {
      if (!organizationId) {
        throw new Error('Немає організації для документа.');
      }
      const document = await createInventory('documents', {
        organization_id: organizationId,
        document_type: documentType,
        source_warehouse_id: needsSource(documentType) ? sourceWarehouseId : undefined,
        destination_warehouse_id: needsDestination(documentType)
          ? destinationWarehouseId
          : undefined,
      });
      await addDocumentLine(document.id, { item_id: itemId, quantity });
      if (postAfterSave) {
        return postDocument(document.id);
      }
      return document;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['inventory'] });
      if (!embedded) {
        onClose();
      }
    },
  });

  const content = (
    <Stack spacing={2} sx={{ pt: embedded ? 0 : 1 }}>
      <FormControl fullWidth>
        <InputLabel>Операція</InputLabel>
        <Select
          disabled={Boolean(fixedType)}
          label="Операція"
          value={documentType}
          onChange={(event) => setDocumentType(event.target.value)}
        >
          {Object.entries(documentTypeLabels).map(([value, label]) => (
            <MenuItem key={value} value={value}>
              {label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {needsSource(documentType) ? (
        <WarehouseSelect
          label="Звідки"
          value={sourceWarehouseId}
          warehouses={warehouses}
          onChange={setSourceWarehouseId}
        />
      ) : null}
      {needsDestination(documentType) ? (
        <WarehouseSelect
          label="Куди"
          value={destinationWarehouseId}
          warehouses={warehouses}
          onChange={setDestinationWarehouseId}
        />
      ) : null}
      <FormControl fullWidth>
        <InputLabel>Номенклатура</InputLabel>
        <Select
          label="Номенклатура"
          value={itemId}
          onChange={(event) => setItemId(event.target.value)}
        >
          {items.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.sku} · {item.name} · {unitSymbol(units, item.unit_of_measure_id)}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <TextField
        label="Кількість"
        type="number"
        value={quantity}
        onChange={(event) => setQuantity(event.target.value)}
      />
      {!embedded ? (
        <Stack alignItems="center" direction="row" spacing={1}>
          <Checkbox
            checked={postAfterSave}
            onChange={(event) => setPostAfterSave(event.target.checked)}
          />
          <Typography>Провести документ після збереження</Typography>
        </Stack>
      ) : null}
      {mutation.error ? <FriendlyError error={mutation.error as ApiError} /> : null}
    </Stack>
  );

  if (embedded) {
    return (
      <Paper variant="outlined" sx={{ p: 2 }}>
        {content}
        <Button
          disabled={
            !canSubmitDocument(documentType, sourceWarehouseId, destinationWarehouseId, itemId) ||
            mutation.isPending
          }
          sx={{ mt: 2 }}
          variant="contained"
          onClick={() => mutation.mutate()}
        >
          Провести переміщення
        </Button>
      </Paper>
    );
  }

  return (
    <Dialog fullWidth maxWidth="sm" open={open} onClose={onClose}>
      <DialogTitle>Новий складський документ</DialogTitle>
      <DialogContent>{content}</DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Закрити</Button>
        <Button
          disabled={
            !canSubmitDocument(documentType, sourceWarehouseId, destinationWarehouseId, itemId) ||
            mutation.isPending
          }
          variant="contained"
          onClick={() => mutation.mutate()}
        >
          Зберегти
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function ItemDialog({
  categories,
  error,
  loading,
  onClose,
  onSubmit,
  open,
  organizationId,
  units,
  warehouses,
}: {
  categories: Category[];
  error: ApiError | null;
  loading: boolean;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
  open: boolean;
  organizationId?: string;
  units: Unit[];
  warehouses: Warehouse[];
}) {
  const [sku, setSku] = useState('');
  const [name, setName] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [unitId, setUnitId] = useState('');
  const [itemType, setItemType] = useState('component');
  const [minimumStock, setMinimumStock] = useState('0');

  return (
    <Dialog fullWidth maxWidth="md" open={open} onClose={onClose}>
      <DialogTitle>Створити номенклатурну позицію</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {!organizationId ? (
            <Alert severity="warning">Спочатку потрібен майданчик або склад.</Alert>
          ) : null}
          {categories.length === 0 || units.length === 0 ? (
            <Alert severity="info">
              Для створення позиції потрібні категорія та одиниця виміру.
            </Alert>
          ) : null}
          <Typography fontWeight={800}>Основне</Typography>
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 2fr' } }}>
            <TextField label="Код" value={sku} onChange={(event) => setSku(event.target.value)} />
            <TextField
              label="Назва"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </Box>
          <Typography fontWeight={800}>Облік</Typography>
          <Box
            sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr 1fr' } }}
          >
            <FormControl fullWidth>
              <InputLabel>Категорія</InputLabel>
              <Select
                label="Категорія"
                value={categoryId}
                onChange={(event) => setCategoryId(event.target.value)}
              >
                {categories.map((category) => (
                  <MenuItem key={category.id} value={category.id}>
                    {category.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Тип</InputLabel>
              <Select
                label="Тип"
                value={itemType}
                onChange={(event) => setItemType(event.target.value)}
              >
                <MenuItem value="raw_material">Матеріал</MenuItem>
                <MenuItem value="component">Комплектуюча</MenuItem>
                <MenuItem value="finished_good">Готовий виріб</MenuItem>
                <MenuItem value="tool">Інструмент</MenuItem>
                <MenuItem value="packaging">Пакування</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>Одиниця</InputLabel>
              <Select
                label="Одиниця"
                value={unitId}
                onChange={(event) => setUnitId(event.target.value)}
              >
                {units.map((unit) => (
                  <MenuItem key={unit.id} value={unit.id}>
                    {unit.name} · {unit.symbol}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Typography fontWeight={800}>Запаси</Typography>
          <Box sx={{ display: 'grid', gap: 2, gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' } }}>
            <TextField
              label="Мінімальний залишок"
              type="number"
              value={minimumStock}
              onChange={(event) => setMinimumStock(event.target.value)}
            />
            <FormControl fullWidth>
              <InputLabel>Склад за замовчуванням</InputLabel>
              <Select label="Склад за замовчуванням" value="" disabled>
                {warehouses.map((warehouse) => (
                  <MenuItem key={warehouse.id} value={warehouse.id}>
                    {warehouse.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          {error ? <FriendlyError error={error} /> : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Скасувати</Button>
        <Button
          disabled={
            !organizationId || !sku.trim() || !name.trim() || !categoryId || !unitId || loading
          }
          variant="contained"
          onClick={() =>
            onSubmit({
              organization_id: organizationId,
              sku,
              name,
              category_id: categoryId,
              unit_of_measure_id: unitId,
              item_type: itemType,
              minimum_stock: minimumStock,
            })
          }
        >
          Зберегти
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function DocumentTable({
  compact = false,
  documents,
  onCancel,
  onPost,
  warehouses,
}: {
  compact?: boolean;
  documents: InventoryDocument[];
  onCancel?: (document: InventoryDocument) => void;
  onPost?: (document: InventoryDocument) => void;
  warehouses: Warehouse[];
}) {
  if (documents.length === 0) {
    return <EmptyState text="Складських документів ще немає." />;
  }
  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Номер</TableCell>
            <TableCell>Дата</TableCell>
            <TableCell>Тип</TableCell>
            {!compact ? <TableCell>Звідки</TableCell> : null}
            {!compact ? <TableCell>Куди</TableCell> : null}
            <TableCell>Статус</TableCell>
            {!compact ? <TableCell align="right">Дії</TableCell> : null}
          </TableRow>
        </TableHead>
        <TableBody>
          {documents.map((document) => (
            <TableRow key={document.id}>
              <TableCell>{document.document_number}</TableCell>
              <TableCell>{new Date(document.document_date).toLocaleDateString('uk-UA')}</TableCell>
              <TableCell>
                {documentTypeLabels[document.document_type] ?? document.document_type}
              </TableCell>
              {!compact ? (
                <TableCell>{nameById(warehouses, document.source_warehouse_id)}</TableCell>
              ) : null}
              {!compact ? (
                <TableCell>{nameById(warehouses, document.destination_warehouse_id)}</TableCell>
              ) : null}
              <TableCell>
                <Chip label={statusLabels[document.status] ?? document.status} size="small" />
              </TableCell>
              {!compact ? (
                <TableCell align="right">
                  {document.status === 'draft' ? (
                    <Button onClick={() => onPost?.(document)}>Провести</Button>
                  ) : null}
                  {document.status === 'posted' ? (
                    <Button color="warning" onClick={() => onCancel?.(document)}>
                      Скасувати
                    </Button>
                  ) : null}
                </TableCell>
              ) : null}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export function StockTable({
  balances,
  items,
  locations,
  units,
  warehouses,
}: {
  balances: StockBalance[];
  items: Item[];
  locations: Location[];
  units: Unit[];
  warehouses: Warehouse[];
}) {
  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Код</TableCell>
            <TableCell>Номенклатура</TableCell>
            <TableCell>Склад</TableCell>
            <TableCell>Місце зберігання</TableCell>
            <TableCell>Кількість</TableCell>
            <TableCell>Одиниця</TableCell>
            <TableCell>Мінімальний залишок</TableCell>
            <TableCell>Стан</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {balances.length === 0 ? (
            <EmptyTable colSpan={8} text="Залишків за фільтром немає." />
          ) : (
            balances.map((balance) => {
              const item = items.find((candidate) => candidate.id === balance.item_id);
              const quantity = Number(balance.quantity);
              const minimum = Number(item?.minimum_stock ?? 0);
              return (
                <TableRow key={balance.id}>
                  <TableCell>{item?.sku ?? '—'}</TableCell>
                  <TableCell>{item?.name ?? '—'}</TableCell>
                  <TableCell>{nameById(warehouses, balance.warehouse_id)}</TableCell>
                  <TableCell>
                    {nameById(locations, balance.location_id) || 'Без деталізації'}
                  </TableCell>
                  <TableCell>{formatQuantity(quantity)}</TableCell>
                  <TableCell>{item ? unitSymbol(units, item.unit_of_measure_id) : '—'}</TableCell>
                  <TableCell>{formatQuantity(minimum)}</TableCell>
                  <TableCell>
                    <Chip
                      color={
                        quantity <= 0
                          ? 'error'
                          : minimum > 0 && quantity < minimum
                            ? 'warning'
                            : 'success'
                      }
                      label={
                        quantity <= 0
                          ? 'Немає в наявності'
                          : minimum > 0 && quantity < minimum
                            ? 'Низький залишок'
                            : 'Достатній залишок'
                      }
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export function WarehouseSelect({
  label,
  onChange,
  value,
  warehouses,
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
  warehouses: Warehouse[];
}) {
  return (
    <FormControl fullWidth>
      <InputLabel>{label}</InputLabel>
      <Select label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        {warehouses.map((warehouse) => (
          <MenuItem key={warehouse.id} value={warehouse.id}>
            {warehouse.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

export function PageHeader({
  action,
  icon,
  subtitle,
  title,
}: {
  action?: ReactNode;
  icon?: ReactNode;
  subtitle: string;
  title: string;
}) {
  return (
    <Toolbar disableGutters sx={{ justifyContent: 'space-between', gap: 2 }}>
      <Stack direction="row" spacing={1.5}>
        {icon ?? <InventoryIcon color="primary" />}
        <Box>
          <Typography variant="h4">{title}</Typography>
          <Typography color="text.secondary">{subtitle}</Typography>
        </Box>
      </Stack>
      {action}
    </Toolbar>
  );
}

export function MetricCard({
  label,
  tone,
  value,
}: {
  label: string;
  tone?: 'warning';
  value: number;
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        borderColor: tone === 'warning' ? 'warning.main' : 'divider',
        p: 2,
      }}
    >
      <Typography color="text.secondary" variant="body2">
        {label}
      </Typography>
      <Typography fontWeight={900} variant="h4">
        {value}
      </Typography>
    </Paper>
  );
}

export function StateChip({ active }: { active: boolean }) {
  return (
    <Chip
      color={active ? 'success' : 'default'}
      label={active ? 'Активна' : 'Неактивна'}
      size="small"
    />
  );
}

export function LoadingState() {
  return (
    <Stack alignItems="center" sx={{ py: 6 }}>
      <CircularProgress />
    </Stack>
  );
}

export function EmptyState({ text }: { text: string }) {
  return (
    <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
      {text}
    </Typography>
  );
}

export function EmptyTable({ colSpan, text }: { colSpan: number; text: string }) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan}>
        <EmptyState text={text} />
      </TableCell>
    </TableRow>
  );
}

export function FriendlyError({ error }: { error: ApiError | Error }) {
  const message =
    'message' in error && error.message
      ? error.message
      : 'Не вдалося виконати операцію. Дані не були змінені.';
  return <Alert severity="error">{message}</Alert>;
}

export function useInventoryLookups() {
  const sitesQuery = useInventoryList('sites');
  const warehousesQuery = useInventoryList('warehouses');
  const locationsQuery = useInventoryList('locations');
  const categoriesQuery = useInventoryList('categories');
  const unitsQuery = useInventoryList('units');
  const itemsQuery = useInventoryList('items');
  const organizationsQuery = useQuery({
    queryKey: ['organizations', 'inventory-lookup'],
    queryFn: () =>
      listEntities('organizations', {
        filters: {},
        page: 1,
        pageSize: 1,
        sortBy: 'name',
        sortDirection: 'asc',
      }),
    retry: false,
  });
  const sites = sitesQuery.data?.items ?? [];
  const warehouses = warehousesQuery.data?.items ?? [];

  return {
    categories: categoriesQuery.data?.items ?? [],
    items: itemsQuery.data?.items ?? [],
    loading:
      sitesQuery.isLoading ||
      warehousesQuery.isLoading ||
      locationsQuery.isLoading ||
      categoriesQuery.isLoading ||
      unitsQuery.isLoading ||
      itemsQuery.isLoading,
    locations: locationsQuery.data?.items ?? [],
    organizationId:
      sites[0]?.organization_id ??
      warehouses[0]?.organization_id ??
      organizationsQuery.data?.items[0]?.id,
    sites,
    units: unitsQuery.data?.items ?? [],
    warehouses,
  };
}

export function useInventoryList<K extends Parameters<typeof listInventory>[0]>(
  kind: K,
  filters: Record<string, string | boolean | null | undefined> = {},
) {
  return useQuery({
    queryKey: ['inventory', kind, filters],
    queryFn: () => listInventory(kind, { filters, pageSize: 100, sortDirection: 'asc' }),
  });
}

export function nameById(rows: Array<{ id: string; name: string }>, id?: string | null) {
  if (!id) {
    return '';
  }
  return rows.find((row) => row.id === id)?.name ?? '';
}

export function unitSymbol(units: Unit[], unitId: string) {
  return units.find((unit) => unit.id === unitId)?.symbol ?? '';
}

export function totalsByItem(balances: StockBalance[]) {
  return balances.reduce<Record<string, number>>((result, balance) => {
    result[balance.item_id] = (result[balance.item_id] ?? 0) + Number(balance.quantity);
    return result;
  }, {});
}

export function formatQuantity(value: string | number) {
  return Number(value).toLocaleString('uk-UA', { maximumFractionDigits: 3 });
}

export function itemTypeLabel(value: string) {
  const labels: Record<string, string> = {
    component: 'Комплектуюча',
    consumable: 'Витратний матеріал',
    finished_good: 'Готовий виріб',
    packaging: 'Пакування',
    raw_material: 'Матеріал',
    service: 'Послуга',
    tool: 'Інструмент',
  };
  return labels[value] ?? value;
}

export function needsSource(documentType: string) {
  return ['issue', 'transfer', 'adjustment_out', 'return_out'].includes(documentType);
}

export function needsDestination(documentType: string) {
  return ['receipt', 'transfer', 'adjustment_in', 'return_in'].includes(documentType);
}

export function canSubmitDocument(
  documentType: string,
  sourceWarehouseId: string,
  destinationWarehouseId: string,
  itemId: string,
) {
  if (!itemId) {
    return false;
  }
  if (needsSource(documentType) && !sourceWarehouseId) {
    return false;
  }
  if (needsDestination(documentType) && !destinationWarehouseId) {
    return false;
  }
  if (documentType === 'transfer' && sourceWarehouseId === destinationWarehouseId) {
    return false;
  }
  return true;
}
