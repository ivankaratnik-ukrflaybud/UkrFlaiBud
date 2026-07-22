import DownloadIcon from '@mui/icons-material/Download';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PrintIcon from '@mui/icons-material/Print';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import {
  Alert,
  Box,
  Button,
  Chip,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { listEntities } from '../organizations/api';
import {
  downloadProductionOrder,
  fetchProductionDashboard,
  listProductionMaterials,
  listProductionOrders,
  reserveMaterials,
  transitionProductionOrder,
} from './api';
import type { ProductionOrder } from './types';

const CONFIGURED_ORGANIZATION_ID = import.meta.env.VITE_DEFAULT_ORGANIZATION_ID ?? '';

const statusLabels: Record<string, string> = {
  draft: 'Чернетка',
  planned: 'Заплановано',
  released: 'Випущено',
  materials_reserved: 'Матеріали зарезервовано',
  in_progress: 'У роботі',
  partially_completed: 'Частково завершено',
  completed: 'Завершено',
  suspended: 'Призупинено',
  cancelled: 'Скасовано',
};

export function ProductionDashboardPage() {
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const organizations = useQuery({
    enabled: !CONFIGURED_ORGANIZATION_ID,
    queryFn: () =>
      listEntities('organizations', {
        filters: { is_active: true },
        page: 1,
        pageSize: 1,
        sortBy: 'name',
        sortDirection: 'asc',
      }),
    queryKey: ['production-organizations-fallback'],
  });
  const organizationId = CONFIGURED_ORGANIZATION_ID || organizations.data?.items[0]?.id || '';
  const dashboard = useQuery({
    enabled: Boolean(organizationId),
    queryFn: () => fetchProductionDashboard(organizationId),
    queryKey: ['production-dashboard', organizationId],
  });
  const orders = useQuery({
    queryFn: () => listProductionOrders({ organizationId: organizationId || undefined }),
    queryKey: ['production-orders', organizationId],
  });
  const selectedOrder = useMemo(
    () => orders.data?.items.find((order) => order.id === selectedOrderId) ?? orders.data?.items[0],
    [orders.data?.items, selectedOrderId],
  );
  const materials = useQuery({
    enabled: Boolean(selectedOrder?.id),
    queryFn: () => listProductionMaterials(selectedOrder?.id ?? ''),
    queryKey: ['production-materials', selectedOrder?.id],
  });
  const action = useMutation({
    mutationFn: ({ orderId, nextAction }: { orderId: string; nextAction: string }) =>
      transitionProductionOrder(orderId, nextAction),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['production-orders'] });
      await queryClient.invalidateQueries({ queryKey: ['production-dashboard'] });
    },
  });
  const reserve = useMutation({
    mutationFn: reserveMaterials,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['production-materials'] });
      await queryClient.invalidateQueries({ queryKey: ['production-orders'] });
    },
  });

  if (!organizationId) {
    return (
      <Alert severity="info">
        Для огляду виробництва задайте VITE_DEFAULT_ORGANIZATION_ID або відкрийте замовлення через
        організаційний контекст.
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4">Огляд виробництва</Typography>
        <Typography color="text.secondary">
          Виробничі замовлення, матеріальне забезпечення, етапи та готова продукція.
        </Typography>
      </Box>
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { md: 'repeat(4, minmax(0, 1fr))', sm: 'repeat(2, 1fr)', xs: '1fr' },
        }}
      >
        {[
          ['Активні замовлення', dashboard.data?.active_orders],
          ['Заплановані', dashboard.data?.planned],
          ['У роботі', dashboard.data?.in_progress],
          ['Частково завершені', dashboard.data?.partially_completed],
          ['Прострочені', dashboard.data?.overdue],
          ['З дефіцитом матеріалів', dashboard.data?.with_material_shortage],
          ['Завершені сьогодні', dashboard.data?.completed_today],
        ].map(([label, value]) => (
          <Box key={label}>
            <Paper sx={{ borderRadius: 1, p: 2 }}>
              <Typography color="text.secondary" variant="body2">
                {label}
              </Typography>
              <Typography variant="h4">{value ?? 0}</Typography>
            </Paper>
          </Box>
        ))}
      </Box>
      <Paper sx={{ borderRadius: 1, overflow: 'hidden' }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="h6">Виробничі замовлення</Typography>
        </Box>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Номер</TableCell>
              <TableCell>Виріб</TableCell>
              <TableCell>Версія специфікації</TableCell>
              <TableCell>Кількість</TableCell>
              <TableCell>Виконано</TableCell>
              <TableCell>Статус</TableCell>
              <TableCell align="right">Дії</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(orders.data?.items ?? []).map((order) => (
              <TableRow
                hover
                key={order.id}
                selected={selectedOrder?.id === order.id}
                onClick={() => setSelectedOrderId(order.id)}
              >
                <TableCell>{order.order_number}</TableCell>
                <TableCell>{order.name}</TableCell>
                <TableCell>v{order.bom_version_number}</TableCell>
                <TableCell>{formatNumber(order.planned_quantity)}</TableCell>
                <TableCell sx={{ minWidth: 180 }}>
                  <Stack spacing={0.5}>
                    <span>
                      {formatNumber(order.completed_quantity)} /{' '}
                      {formatNumber(order.planned_quantity)}
                    </span>
                    <LinearProgress value={progress(order)} variant="determinate" />
                  </Stack>
                </TableCell>
                <TableCell>
                  <Chip label={statusLabels[order.status] ?? order.status} size="small" />
                </TableCell>
                <TableCell align="right">
                  <Stack direction="row" justifyContent="flex-end" spacing={1}>
                    <Button
                      size="small"
                      startIcon={<PlayArrowIcon />}
                      onClick={(event) => {
                        event.stopPropagation();
                        action.mutate({ orderId: order.id, nextAction: nextAction(order.status) });
                      }}
                    >
                      Запустити
                    </Button>
                    <Button
                      size="small"
                      startIcon={<RestartAltIcon />}
                      onClick={(event) => {
                        event.stopPropagation();
                        reserve.mutate(order.id);
                      }}
                    >
                      Резерв
                    </Button>
                    <Button
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={(event) => {
                        event.stopPropagation();
                        void downloadProductionOrder(order.id, 'pdf');
                      }}
                    >
                      PDF
                    </Button>
                    <Button
                      size="small"
                      startIcon={<PrintIcon />}
                      onClick={(event) => {
                        event.stopPropagation();
                        window.open(`/api/v1/production/orders/${order.id}/preview`, '_blank');
                      }}
                    >
                      Друк
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      {selectedOrder ? (
        <Paper sx={{ borderRadius: 1, overflow: 'hidden' }}>
          <Box sx={{ alignItems: 'center', display: 'flex', justifyContent: 'space-between', p: 2 }}>
            <Typography variant="h6">Матеріали до виробництва: {selectedOrder.order_number}</Typography>
            <Button
              size="small"
              startIcon={<OpenInNewIcon />}
              onClick={() => window.open(`/api/v1/production/orders/${selectedOrder.id}/preview`, '_blank')}
            >
              Документ
            </Button>
          </Box>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>№</TableCell>
                <TableCell>Код</TableCell>
                <TableCell>Найменування</TableCell>
                <TableCell>Потрібно</TableCell>
                <TableCell>Зарезервовано</TableCell>
                <TableCell>Видано</TableCell>
                <TableCell>Доступно</TableCell>
                <TableCell>Дефіцит</TableCell>
                <TableCell>Стан</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(materials.data ?? []).map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.line_number}</TableCell>
                  <TableCell>{item.item_code_snapshot}</TableCell>
                  <TableCell>{item.display_name}</TableCell>
                  <TableCell>{formatNumber(item.planned_quantity)} {item.unit_symbol_snapshot}</TableCell>
                  <TableCell>{formatNumber(item.reserved_quantity)}</TableCell>
                  <TableCell>{formatNumber(item.issued_quantity)}</TableCell>
                  <TableCell>{formatNumber(item.available_quantity)}</TableCell>
                  <TableCell>{formatNumber(item.shortage_quantity)}</TableCell>
                  <TableCell>
                    <Chip
                      color={Number(item.shortage_quantity) > 0 ? 'warning' : 'success'}
                      label={materialStatus(item)}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      ) : null}
    </Stack>
  );
}

function progress(order: ProductionOrder) {
  const planned = Number(order.planned_quantity);
  if (!planned) return 0;
  return Math.min(100, (Number(order.completed_quantity) / planned) * 100);
}

function nextAction(status: string) {
  if (status === 'draft') return 'plan';
  if (status === 'planned') return 'release';
  return 'start';
}

function formatNumber(value: string | number) {
  return new Intl.NumberFormat('uk-UA', { maximumFractionDigits: 3 }).format(Number(value));
}

function materialStatus(item: { source_type: string; shortage_quantity: string; issued_quantity: string }) {
  if (item.source_type === 'manual') return 'Ручна позиція';
  if (Number(item.issued_quantity) > 0) return 'Видано';
  if (Number(item.shortage_quantity) > 0) return 'Дефіцит';
  return 'Забезпечено';
}
