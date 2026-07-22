import BuildIcon from '@mui/icons-material/Build';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DownloadIcon from '@mui/icons-material/Download';
import FactoryIcon from '@mui/icons-material/Factory';
import InventoryIcon from '@mui/icons-material/Inventory';
import PauseIcon from '@mui/icons-material/Pause';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import PrintIcon from '@mui/icons-material/Print';
import ReportProblemIcon from '@mui/icons-material/ReportProblem';
import {
  Alert,
  Box,
  Button,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { useAuth } from '../identity/AuthContext';
import { listEntities } from '../organizations/api';
import {
  cncAction,
  downloadCncWorkOrder,
  fetchCncDashboard,
  fetchReadiness,
  issueCncMaterial,
  listCncMachines,
  listCncMaterialTransactions,
  listCncParts,
  listCncPrograms,
  listCncQueue,
  listCncSheetPlans,
  listCncWorkOrders,
  reportCncOutput,
} from './api';
import type { CncDashboard, CncWorkOrder } from './types';

const statusLabels: Record<string, string> = {
  draft: 'Чернетка',
  planned: 'Заплановано',
  queued: 'У черзі',
  setup: 'Налаштування',
  running: 'В роботі',
  paused: 'Пауза',
  partially_completed: 'Частково виконано',
  completed: 'Завершено',
  blocked: 'Заблоковано',
  cancelled: 'Скасовано',
  available: 'Доступний',
  fault: 'Аварія',
  maintenance: 'Обслуговування',
};

function useOrganizationId() {
  const auth = useAuth();
  const authOrganizationId =
    (auth.user as { organization_id?: string } | undefined)?.organization_id ?? '';
  const organizations = useQuery({
    enabled: !authOrganizationId,
    queryFn: () =>
      listEntities('organizations', {
        filters: { is_active: true },
        page: 1,
        pageSize: 1,
        sortBy: 'name',
        sortDirection: 'asc',
      }),
    queryKey: ['cnc-organizations-fallback'],
  });
  return authOrganizationId || organizations.data?.items[0]?.id || '';
}

export function CncDashboardPage() {
  return <CncModule initialTab="dashboard" />;
}

export function CncQueuePage() {
  return <CncModule initialTab="queue" />;
}

export function CncWorkOrdersPage() {
  return <CncModule initialTab="orders" />;
}

export function CncSheetsPage() {
  return <CncModule initialTab="sheets" />;
}

export function CncPartsPage() {
  return <CncModule initialTab="parts" />;
}

export function CncProgramsPage() {
  return <CncModule initialTab="programs" />;
}

export function CncMachinesPage() {
  return <CncModule initialTab="machines" />;
}

export function CncToolsPage() {
  return <CncModule initialTab="tools" />;
}

export function CncOffcutsPage() {
  return <CncModule initialTab="offcuts" />;
}

export function CncSettingsPage() {
  return <CncModule initialTab="settings" />;
}

function CncModule({ initialTab }: { initialTab: string }) {
  const [tab, setTab] = useState(initialTab);
  const organizationId = useOrganizationId();
  const dashboard = useQuery({
    enabled: Boolean(organizationId),
    queryFn: () => fetchCncDashboard(organizationId),
    queryKey: ['cnc-dashboard', organizationId],
  });

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4">ЧПК</Typography>
          <Typography color="text.secondary" variant="body2">
            Верстати, черга, завдання, матеріали та випуск деталей.
          </Typography>
        </Box>
        <Chip color="primary" icon={<PrecisionManufacturingIcon />} label="Операції ЧПК" />
      </Stack>

      {dashboard.isError ? <Alert severity="warning">Не вдалося завантажити дані ЧПК.</Alert> : null}
      {dashboard.isLoading ? <LinearProgress /> : null}

      <Tabs onChange={(_, value) => setTab(value)} value={tab} variant="scrollable">
        <Tab label="Огляд" value="dashboard" />
        <Tab label="Черга" value="queue" />
        <Tab label="Завдання" value="orders" />
        <Tab label="Карти розкрою" value="sheets" />
        <Tab label="Деталі" value="parts" />
        <Tab label="Програми" value="programs" />
        <Tab label="Верстати" value="machines" />
        <Tab label="Інструмент" value="tools" />
        <Tab label="Залишки" value="offcuts" />
        <Tab label="Налаштування" value="settings" />
      </Tabs>

      {tab === 'dashboard' ? <DashboardCards data={dashboard.data} /> : null}
      {tab === 'queue' ? <QueueView organizationId={organizationId} /> : null}
      {tab === 'orders' ? <WorkOrdersView organizationId={organizationId} /> : null}
      {tab === 'sheets' ? <DirectoryView organizationId={organizationId} type="sheets" /> : null}
      {tab === 'parts' ? <DirectoryView organizationId={organizationId} type="parts" /> : null}
      {tab === 'programs' ? <DirectoryView organizationId={organizationId} type="programs" /> : null}
      {tab === 'machines' ? <DirectoryView organizationId={organizationId} type="machines" /> : null}
      {tab === 'tools' ? <ToolsPlaceholder /> : null}
      {tab === 'offcuts' ? <OffcutsPlaceholder /> : null}
      {tab === 'settings' ? <SettingsPanel /> : null}
    </Stack>
  );
}

function DashboardCards({ data }: { data?: CncDashboard }) {
  const cards = [
    ['Верстати в роботі', data?.running_machines ?? 0, <FactoryIcon key="running" />],
    ['Доступні верстати', data?.available_machines ?? 0, <PrecisionManufacturingIcon key="available" />],
    ['Завдання в черзі', data?.queued_work_orders ?? 0, <InventoryIcon key="queued" />],
    ['Завдання в роботі', data?.running_work_orders ?? 0, <PlayArrowIcon key="work" />],
    ['Заблоковані', data?.blocked_work_orders ?? 0, <ReportProblemIcon key="blocked" />],
    ['Прострочені', data?.overdue_work_orders ?? 0, <ReportProblemIcon key="overdue" />],
    ['Виконано сьогодні', data?.completed_today ?? 0, <CheckCircleIcon key="done" />],
    ['Брак сьогодні', data?.rejected_today ?? 0, <BuildIcon key="reject" />],
  ];
  return (
    <Grid container spacing={2}>
      {cards.map(([label, value, icon]) => (
        <Grid key={String(label)} size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2 }}>
            <Stack direction="row" justifyContent="space-between">
              <Box>
                <Typography color="text.secondary" variant="body2">
                  {label}
                </Typography>
                <Typography variant="h5">{value}</Typography>
              </Box>
              {icon}
            </Stack>
          </Paper>
        </Grid>
      ))}
    </Grid>
  );
}

function QueueView({ organizationId }: { organizationId: string }) {
  const queue = useQuery({
    enabled: Boolean(organizationId),
    queryFn: () => listCncQueue(organizationId),
    queryKey: ['cnc-queue', organizationId],
  });
  return (
    <Stack spacing={2}>
      <Box
        sx={{
          display: 'grid',
          gap: 1,
          gridTemplateColumns: { md: 'repeat(4, minmax(0, 1fr))', sm: 'repeat(2, 1fr)', xs: '1fr' },
        }}
      >
        {(queue.data?.items ?? []).slice(0, 8).map((item) => (
          <Paper key={item.id} sx={{ borderLeft: 4, borderColor: 'primary.main', p: 1.5 }}>
            <Stack spacing={0.75}>
              <Stack direction="row" justifyContent="space-between">
                <Typography fontWeight={700} variant="body2">{item.work_order_number}</Typography>
                <Chip label={item.queue_position ?? '-'} size="small" />
              </Stack>
              <Typography color="text.secondary" noWrap variant="body2">
                {item.part_name_snapshot ?? item.name}
              </Typography>
              <LinearProgress value={progressValue(item)} variant="determinate" />
            </Stack>
          </Paper>
        ))}
      </Box>
      <WorkOrderTable rows={queue.data?.items ?? []} showQueue />
    </Stack>
  );
}

function WorkOrdersView({ organizationId }: { organizationId: string }) {
  const orders = useQuery({
    enabled: Boolean(organizationId),
    queryFn: () => listCncWorkOrders(organizationId),
    queryKey: ['cnc-orders', organizationId],
  });
  const firstActive = useMemo(
    () => orders.data?.items.find((item) => ['queued', 'setup', 'running', 'paused'].includes(item.status)),
    [orders.data?.items],
  );
  return (
    <Stack spacing={3}>
      {firstActive ? <OperatorPanel workOrder={firstActive} /> : null}
      <WorkOrderTable rows={orders.data?.items ?? []} />
    </Stack>
  );
}

function WorkOrderTable({ rows, showQueue = false }: { rows: CncWorkOrder[]; showQueue?: boolean }) {
  return (
    <Paper sx={{ overflowX: 'auto' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            {showQueue ? <TableCell>Позиція</TableCell> : null}
            <TableCell>Номер</TableCell>
            <TableCell>Деталь / карта розкрою</TableCell>
            <TableCell>Заплановано</TableCell>
            <TableCell>Виготовлено</TableCell>
            <TableCell>Брак</TableCell>
            <TableCell>Статус</TableCell>
            <TableCell align="right">Дії</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.id}>
              {showQueue ? <TableCell>{row.queue_position ?? '-'}</TableCell> : null}
              <TableCell>{row.work_order_number}</TableCell>
              <TableCell>{row.part_name_snapshot ?? row.name}</TableCell>
              <TableCell>{row.planned_quantity}</TableCell>
              <TableCell>{row.completed_quantity}</TableCell>
              <TableCell>{row.rejected_quantity}</TableCell>
              <TableCell>
                <Chip label={statusLabels[row.status] ?? row.status} size="small" />
              </TableCell>
              <TableCell align="right">
                <Stack direction="row" justifyContent="flex-end" spacing={1}>
                  <ExportButton format="pdf" workOrderId={row.id} />
                  <ExportButton format="xlsx" workOrderId={row.id} />
                </Stack>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}

function OperatorPanel({ workOrder }: { workOrder: CncWorkOrder }) {
  const queryClient = useQueryClient();
  const [good, setGood] = useState('1');
  const [rejected, setRejected] = useState('0');
  const readiness = useQuery({
    queryFn: () => fetchReadiness(workOrder.id),
    queryKey: ['cnc-readiness', workOrder.id],
  });
  const mutation = useMutation({
    mutationFn: ({ action, reason }: { action: string; reason?: string }) =>
      cncAction(workOrder.id, action, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cnc-orders'] }),
  });
  const report = useMutation({
    mutationFn: () => reportCncOutput(workOrder.id, good, rejected),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cnc-orders'] }),
  });
  const material = useMutation({
    mutationFn: () => issueCncMaterial(workOrder.id, '1'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['cnc-material-history', workOrder.id] }),
  });
  const materialHistory = useQuery({
    queryFn: () => listCncMaterialTransactions(workOrder.id),
    queryKey: ['cnc-material-history', workOrder.id],
  });

  return (
    <Paper sx={{ p: 2 }}>
      <Stack spacing={2}>
        <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
          <Box>
            <Typography variant="h6">{workOrder.work_order_number}</Typography>
            <Typography color="text.secondary">{workOrder.part_name_snapshot ?? workOrder.name}</Typography>
          </Box>
          <Chip color={readiness.data?.ready ? 'success' : 'warning'} label={readiness.data?.ready ? 'Готово' : 'Потрібна перевірка'} />
        </Stack>
        <Stack direction="row" flexWrap="wrap" gap={1}>
          {readiness.data?.checklist.map((item) => (
            <Chip color={item.ready ? 'success' : 'default'} key={item.code} label={item.label} size="small" />
          ))}
        </Stack>
        <Stack direction="row" flexWrap="wrap" gap={1}>
          <Button onClick={() => mutation.mutate({ action: 'start-setup' })} startIcon={<BuildIcon />} variant="contained">
            Почати налаштування
          </Button>
          <Button onClick={() => mutation.mutate({ action: 'start' })} startIcon={<PlayArrowIcon />} variant="contained">
            Почати обробку
          </Button>
          <Button onClick={() => mutation.mutate({ action: 'pause', reason: 'Пауза оператора' })} startIcon={<PauseIcon />}>
            Пауза
          </Button>
          <Button onClick={() => mutation.mutate({ action: 'resume' })} startIcon={<PlayArrowIcon />}>
            Продовжити
          </Button>
          <Button onClick={() => material.mutate()} startIcon={<InventoryIcon />}>
            Видати матеріал
          </Button>
        </Stack>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          <TextField label="Готово" onChange={(event) => setGood(event.target.value)} size="small" type="number" value={good} />
          <TextField label="Брак" onChange={(event) => setRejected(event.target.value)} size="small" type="number" value={rejected} />
          <Button onClick={() => report.mutate()} startIcon={<CheckCircleIcon />} variant="outlined">
            Повідомити кількість
          </Button>
          <Button color="success" onClick={() => mutation.mutate({ action: 'complete' })}>
            Завершити
          </Button>
        </Stack>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>РћРїРµСЂР°С†С–СЏ</TableCell>
              <TableCell>РљС–Р»СЊРєС–СЃС‚СЊ</TableCell>
              <TableCell>Р”Р°С‚Р°</TableCell>
              <TableCell>РџСЂРёС‡РёРЅР°</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(materialHistory.data ?? []).map((item) => (
              <TableRow key={item.id}>
                <TableCell>{materialLabel(item.transaction_type)}</TableCell>
                <TableCell>{item.quantity}</TableCell>
                <TableCell>{new Date(item.posted_at).toLocaleString('uk-UA')}</TableCell>
                <TableCell>{item.reason ?? '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Stack>
    </Paper>
  );
}

function progressValue(order: CncWorkOrder) {
  const planned = Number(order.planned_quantity);
  if (!planned) return 0;
  return Math.min(100, ((Number(order.completed_quantity) + Number(order.rejected_quantity)) / planned) * 100);
}

function materialLabel(value: string) {
  const labels: Record<string, string> = {
    issue: 'Р’РёРґР°С‡Р°',
    return: 'РџРѕРІРµСЂРЅРµРЅРЅСЏ',
    scrap: 'Р‘СЂР°Рє',
  };
  return labels[value] ?? value;
}

function DirectoryView({ organizationId, type }: { organizationId: string; type: 'machines' | 'programs' | 'parts' | 'sheets' }) {
  const query = useQuery({
    enabled: Boolean(organizationId),
    queryFn: async () => {
      if (type === 'machines') return listCncMachines(organizationId);
      if (type === 'programs') return listCncPrograms(organizationId);
      if (type === 'parts') return listCncParts(organizationId);
      return listCncSheetPlans(organizationId);
    },
    queryKey: ['cnc-directory', type, organizationId],
  });
  return (
    <Paper sx={{ overflowX: 'auto' }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Код / номер</TableCell>
            <TableCell>Назва</TableCell>
            <TableCell>Статус</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(query.data?.items ?? []).map((item) => (
            <TableRow key={item.id}>
              <TableCell>{'code' in item ? item.code : item.plan_number}</TableCell>
              <TableCell>{item.name}</TableCell>
              <TableCell>
                <Chip label={'status' in item ? statusLabels[item.status] ?? item.status : 'program_status' in item ? item.program_status : ''} size="small" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
}

function ExportButton({ workOrderId, format }: { workOrderId: string; format: 'pdf' | 'xlsx' }) {
  return (
    <Tooltip title={format === 'pdf' ? 'PDF' : 'XLSX'}>
      <Button onClick={() => downloadCncWorkOrder(workOrderId, format)} size="small" startIcon={format === 'pdf' ? <PrintIcon /> : <DownloadIcon />}>
        {format.toUpperCase()}
      </Button>
    </Tooltip>
  );
}

function ToolsPlaceholder() {
  return <Alert severity="info">Довідник інструменту ЧПК доступний через API та готовий до розширення формами.</Alert>;
}

function OffcutsPlaceholder() {
  return <Alert severity="info">Придатні залишки реєструються із завдання ЧПК та доступні для майбутнього пошуку.</Alert>;
}

function SettingsPanel() {
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6">Причини браку</Typography>
      <Stack direction="row" flexWrap="wrap" gap={1} mt={2}>
        {['пошкодження матеріалу', 'помилка програми', 'поломка інструмента', 'помилка оператора', 'невідповідність розміру', 'інше'].map((reason) => (
          <Chip key={reason} label={reason} />
        ))}
      </Stack>
    </Paper>
  );
}
