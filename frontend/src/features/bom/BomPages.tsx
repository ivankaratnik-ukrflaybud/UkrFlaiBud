import AddIcon from '@mui/icons-material/Add';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteIcon from '@mui/icons-material/Delete';
import HistoryIcon from '@mui/icons-material/History';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import PrintIcon from '@mui/icons-material/Print';
import SaveIcon from '@mui/icons-material/Save';
import TableChartIcon from '@mui/icons-material/TableChart';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  GlobalStyles,
  InputLabel,
  Menu,
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
  Tooltip,
  Typography,
} from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Link as RouterLink, useNavigate, useParams } from 'react-router-dom';

import { listInventory } from '../inventory/api';
import type { Item, Unit } from '../inventory/types';
import { listEntities } from '../organizations/api';
import { queryClient } from '../../services/queryClient';
import {
  addBomLine,
  approveBomVersion,
  archiveBomVersion,
  archiveBomSpecification,
  compareBomVersions,
  copyBomSpecification,
  createBomSpecification,
  createBomVersion,
  deleteBomLine,
  downloadBomFile,
  duplicateBomLine,
  fetchBomPreviewHtml,
  getBomSpecification,
  listBomLines,
  listBomSpecifications,
  listBomVersions,
  reorderBomLines,
  updateBomLine,
  updateBomSpecification,
} from './api';
import type { BomLine, BomSpecification, BomVersion } from './types';

const statusLabels: Record<string, string> = {
  draft: 'Чернетка',
  under_review: 'На перегляді',
  approved: 'Затверджено',
  superseded: 'Замінено',
  archived: 'Архів',
};

export function BomListPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [copySource, setCopySource] = useState<BomSpecification | null>(null);
  const organizations = useQuery({
    queryKey: ['organizations', 'bom-picker'],
    queryFn: () =>
      listEntities('organizations', {
        page: 1,
        pageSize: 50,
        sortBy: 'name',
        sortDirection: 'asc',
        filters: { is_active: true },
      }),
  });
  const specs = useQuery({
    queryKey: ['bom', 'specifications', search, status],
    queryFn: () => listBomSpecifications({ search, status }),
  });
  const createMutation = useMutation({
    mutationFn: createBomSpecification,
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ['bom', 'specifications'] });
      setCreateOpen(false);
      navigate(`/specifications/${created.id}`);
    },
  });
  const copyMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => copyBomSpecification(copySource?.id ?? '', payload),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ['bom', 'specifications'] });
      setCopySource(null);
      navigate(`/specifications/${created.id}`);
    },
  });
  const archiveMutation = useMutation({
    mutationFn: archiveBomSpecification,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bom', 'specifications'] }),
  });

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4">Специфікації</Typography>
          <Typography color="text.secondary">Керування BOM, версіями та друком виробів.</Typography>
        </Box>
        <Button startIcon={<AddIcon />} variant="contained" onClick={() => setCreateOpen(true)}>
          Створити специфікацію
        </Button>
      </Stack>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField
            fullWidth
            label="Пошук за кодом або назвою"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <FormControl sx={{ minWidth: 220 }}>
            <InputLabel>Статус</InputLabel>
            <Select label="Статус" value={status} onChange={(event) => setStatus(event.target.value)}>
              <MenuItem value="">Усі</MenuItem>
              <MenuItem value="draft">Чернетка</MenuItem>
              <MenuItem value="under_review">На перегляді</MenuItem>
              <MenuItem value="approved">Затверджено</MenuItem>
              <MenuItem value="archived">Архів</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>
      <Paper variant="outlined">
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Код</TableCell>
                <TableCell>Назва</TableCell>
                <TableCell>Поточна версія</TableCell>
                <TableCell>Статус</TableCell>
                <TableCell>Дата зміни</TableCell>
                <TableCell align="right">Дії</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(specs.data?.items ?? []).map((spec) => (
                <TableRow hover key={spec.id}>
                  <TableCell>{spec.code}</TableCell>
                  <TableCell>{spec.name}</TableCell>
                  <TableCell>v{spec.current_version_number}</TableCell>
                  <TableCell>
                    <Chip label={statusLabels[spec.status]} size="small" />
                  </TableCell>
                  <TableCell>{new Date(spec.updated_at).toLocaleDateString('uk-UA')}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" justifyContent="flex-end" spacing={1}>
                      <Button size="small" onClick={() => navigate(`/specifications/${spec.id}`)}>
                        Відкрити
                      </Button>
                      <Button size="small" startIcon={<HistoryIcon />} onClick={() => navigate(`/specifications/${spec.id}/versions`)}>
                        Версії
                      </Button>
                      <Tooltip title="Завантажити PDF">
                        <Button size="small" onClick={() => navigate(`/specifications/${spec.id}/print`)}>
                          <PictureAsPdfIcon fontSize="small" />
                        </Button>
                      </Tooltip>
                      <Tooltip title="Копіювати">
                        <Button size="small" onClick={() => setCopySource(spec)}>
                          <ContentCopyIcon fontSize="small" />
                        </Button>
                      </Tooltip>
                      <Tooltip title="Архівувати">
                        <Button size="small" onClick={() => archiveMutation.mutate(spec.id)}>
                          <DeleteIcon fontSize="small" />
                        </Button>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
              {(specs.data?.items ?? []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>Специфікації ще не створено.</TableCell>
                </TableRow>
              ) : null}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
      <SpecificationDialog
        loading={createMutation.isPending}
        open={createOpen}
        organizations={organizations.data?.items ?? []}
        onClose={() => setCreateOpen(false)}
        onSubmit={(payload) => createMutation.mutate(payload)}
      />
      <CopyDialog
        loading={copyMutation.isPending}
        open={Boolean(copySource)}
        source={copySource}
        onClose={() => setCopySource(null)}
        onSubmit={(payload) => copyMutation.mutate(payload)}
      />
    </Stack>
  );
}

export function BomEditorPage() {
  const { specificationId = '' } = useParams();
  const [addAnchor, setAddAnchor] = useState<HTMLElement | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [inventoryOpen, setInventoryOpen] = useState(false);
  const [dirty, setDirty] = useState(false);
  const spec = useQuery({
    queryKey: ['bom', 'specification', specificationId],
    queryFn: () => getBomSpecification(specificationId),
    enabled: Boolean(specificationId),
  });
  const versions = useQuery({
    queryKey: ['bom', 'versions', specificationId],
    queryFn: () => listBomVersions(specificationId),
    enabled: Boolean(specificationId),
  });
  const currentVersion = useMemo(
    () => versions.data?.find((version) => version.version_number === spec.data?.current_version_number) ?? versions.data?.[0],
    [spec.data?.current_version_number, versions.data],
  );
  const lines = useQuery({
    queryKey: ['bom', 'lines', currentVersion?.id],
    queryFn: () => listBomLines(currentVersion?.id ?? ''),
    enabled: Boolean(currentVersion?.id),
  });
  const units = useQuery({
    queryKey: ['inventory', 'units', 'bom'],
    queryFn: () => listInventory('units', { pageSize: 100 }),
  });
  const items = useQuery({
    queryKey: ['inventory', 'items', 'bom'],
    queryFn: () => listInventory('items', { pageSize: 100 }),
  });
  const readonly = currentVersion?.status !== 'draft';
  useEffect(() => {
    const handler = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const saveSpec = useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateBomSpecification(specificationId, payload),
    onSuccess: async () => {
      setDirty(false);
      await queryClient.invalidateQueries({ queryKey: ['bom', 'specification', specificationId] });
      await queryClient.invalidateQueries({ queryKey: ['bom', 'specifications'] });
    },
  });
  const addLine = useMutation({
    mutationFn: (payload: Record<string, unknown>) => addBomLine(currentVersion?.id ?? '', payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['bom', 'lines', currentVersion?.id] });
      setManualOpen(false);
      setInventoryOpen(false);
    },
  });
  const updateLine = useMutation({
    mutationFn: ({ line, payload }: { line: BomLine; payload: Record<string, unknown> }) =>
      updateBomLine(currentVersion?.id ?? '', line.id, { ...payload, version: line.version }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bom', 'lines', currentVersion?.id] }),
  });
  const deleteLine = useMutation({
    mutationFn: (lineId: string) => deleteBomLine(currentVersion?.id ?? '', lineId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bom', 'lines', currentVersion?.id] }),
  });
  const duplicateLine = useMutation({
    mutationFn: (lineId: string) => duplicateBomLine(currentVersion?.id ?? '', lineId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bom', 'lines', currentVersion?.id] }),
  });
  const reorderLine = useMutation({
    mutationFn: (lineIds: string[]) => reorderBomLines(currentVersion?.id ?? '', lineIds),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['bom', 'lines', currentVersion?.id] }),
  });
  const approve = useMutation({
    mutationFn: () => approveBomVersion(currentVersion?.id ?? ''),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['bom', 'versions', specificationId] });
      await queryClient.invalidateQueries({ queryKey: ['bom', 'specification', specificationId] });
    },
  });
  const createVersion = useMutation({
    mutationFn: () =>
      createBomVersion(specificationId, {
        source_version_id: currentVersion?.id,
        change_reason: 'Нова робоча версія',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['bom', 'versions', specificationId] });
      await queryClient.invalidateQueries({ queryKey: ['bom', 'specification', specificationId] });
    },
  });

  const orderedLines = lines.data ?? [];
  const unitById = Object.fromEntries((units.data?.items ?? []).map((unit) => [unit.id, unit]));
  const move = (line: BomLine, direction: -1 | 1) => {
    const index = orderedLines.findIndex((candidate) => candidate.id === line.id);
    const next = [...orderedLines];
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    reorderLine.mutate(next.map((candidate) => candidate.id));
  };

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4">Редактор специфікації</Typography>
          <Typography color="text.secondary">
            {spec.data?.code} · v{currentVersion?.version_number} · {statusLabels[currentVersion?.status ?? 'draft']}
          </Typography>
        </Box>
        <Stack direction="row" flexWrap="wrap" gap={1}>
          {dirty ? <Chip color="warning" label="Є незбережені зміни" /> : null}
          <Button component={RouterLink} to={`/specifications/${specificationId}/versions`}>
            Історія версій
          </Button>
          <Button component={RouterLink} startIcon={<PrintIcon />} to={`/specifications/${specificationId}/print`}>
            Попередній перегляд
          </Button>
          {readonly ? (
            <Button variant="contained" onClick={() => createVersion.mutate()}>
              Створити нову версію
            </Button>
          ) : (
            <Button color="success" variant="contained" onClick={() => approve.mutate()}>
              Затвердити
            </Button>
          )}
        </Stack>
      </Stack>
      {readonly ? <Alert severity="info">Затверджена версія доступна тільки для перегляду.</Alert> : null}
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField
            fullWidth
            disabled={spec.isLoading}
            label="Код специфікації"
            value={spec.data?.code ?? ''}
            onChange={(event) => {
              if (!spec.data) return;
              queryClient.setQueryData(['bom', 'specification', specificationId], { ...spec.data, code: event.target.value });
              setDirty(true);
            }}
          />
          <TextField
            fullWidth
            label="Назва специфікації"
            value={spec.data?.name ?? ''}
            onChange={(event) => {
              if (!spec.data) return;
              queryClient.setQueryData(['bom', 'specification', specificationId], { ...spec.data, name: event.target.value });
              setDirty(true);
            }}
          />
          <Button
            startIcon={<SaveIcon />}
            variant="contained"
            onClick={() =>
              spec.data &&
              saveSpec.mutate({ code: spec.data.code, name: spec.data.name, version: spec.data.version })
            }
          >
            Зберегти
          </Button>
        </Stack>
      </Paper>
      <Paper variant="outlined">
        <Stack direction="row" justifyContent="space-between" sx={{ p: 2 }}>
          <Typography variant="h6">Позиції</Typography>
          <Button
            disabled={readonly}
            startIcon={<AddIcon />}
            variant="contained"
            onClick={(event) => setAddAnchor(event.currentTarget)}
          >
            Додати позицію
          </Button>
          <Menu anchorEl={addAnchor} open={Boolean(addAnchor)} onClose={() => setAddAnchor(null)}>
            <MenuItem onClick={() => { setInventoryOpen(true); setAddAnchor(null); }}>
              Обрати з номенклатури
            </MenuItem>
            <MenuItem onClick={() => { setManualOpen(true); setAddAnchor(null); }}>
              Додати вручну
            </MenuItem>
            <MenuItem onClick={() => { setManualOpen(true); setAddAnchor(null); }}>
              Додати вузол або підзбірку
            </MenuItem>
          </Menu>
        </Stack>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>№</TableCell>
                <TableCell>Код</TableCell>
                <TableCell>Назва позиції</TableCell>
                <TableCell>Кількість</TableCell>
                <TableCell>Одиниця</TableCell>
                <TableCell>Тип</TableCell>
                <TableCell>Примітка</TableCell>
                <TableCell align="right">Дії</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {orderedLines.map((line) => (
                <TableRow key={line.id}>
                  <TableCell>{line.line_number}</TableCell>
                  <TableCell>{line.position_code}</TableCell>
                  <TableCell>
                    <TextField
                      fullWidth
                      disabled={readonly}
                      size="small"
                      value={line.display_name}
                      onChange={(event) =>
                        updateLine.mutate({ line, payload: { display_name: event.target.value } })
                      }
                    />
                  </TableCell>
                  <TableCell sx={{ width: 120 }}>
                    <TextField
                      disabled={readonly}
                      size="small"
                      type="number"
                      value={line.quantity}
                      onChange={(event) => updateLine.mutate({ line, payload: { quantity: event.target.value } })}
                    />
                  </TableCell>
                  <TableCell>{unitById[line.unit_of_measure_id]?.symbol ?? ''}</TableCell>
                  <TableCell>{line.source_type === 'manual' ? 'Вручну' : 'Номенклатура'}</TableCell>
                  <TableCell>
                    <TextField
                      fullWidth
                      disabled={readonly}
                      size="small"
                      value={line.notes ?? ''}
                      onChange={(event) => updateLine.mutate({ line, payload: { notes: event.target.value } })}
                    />
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" justifyContent="flex-end" spacing={0.5}>
                      <Button disabled={readonly} size="small" onClick={() => move(line, -1)}>
                        <KeyboardArrowUpIcon fontSize="small" />
                      </Button>
                      <Button disabled={readonly} size="small" onClick={() => move(line, 1)}>
                        <KeyboardArrowDownIcon fontSize="small" />
                      </Button>
                      <Button disabled={readonly} size="small" onClick={() => duplicateLine.mutate(line.id)}>
                        <ContentCopyIcon fontSize="small" />
                      </Button>
                      <Button disabled={readonly} size="small" onClick={() => deleteLine.mutate(line.id)}>
                        <DeleteIcon fontSize="small" />
                      </Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
      <LineDialog
        items={items.data?.items ?? []}
        mode="inventory"
        open={inventoryOpen}
        units={units.data?.items ?? []}
        onClose={() => setInventoryOpen(false)}
        onSubmit={(payload) => addLine.mutate(payload)}
      />
      <LineDialog
        mode="manual"
        open={manualOpen}
        units={units.data?.items ?? []}
        onClose={() => setManualOpen(false)}
        onSubmit={(payload) => addLine.mutate(payload)}
      />
    </Stack>
  );
}

export function BomVersionsPage() {
  const { specificationId = '' } = useParams();
  const versions = useQuery({
    queryKey: ['bom', 'versions', specificationId],
    queryFn: () => listBomVersions(specificationId),
  });
  const [left, setLeft] = useState('');
  const [right, setRight] = useState('');
  const compare = useQuery({
    queryKey: ['bom', 'compare', left, right],
    queryFn: () => compareBomVersions(left, right),
    enabled: Boolean(left && right),
  });
  const archiveVersion = useMutation({
    mutationFn: archiveBomVersion,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['bom', 'versions', specificationId] });
      await queryClient.invalidateQueries({ queryKey: ['bom', 'specification', specificationId] });
    },
  });
  return (
    <Stack spacing={3}>
      <Typography variant="h4">Історія версій</Typography>
      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Версія</TableCell>
              <TableCell>Статус</TableCell>
              <TableCell>Дата створення</TableCell>
              <TableCell>Дата затвердження</TableCell>
              <TableCell>Причина зміни</TableCell>
              <TableCell align="right">Дії</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(versions.data ?? []).map((version) => (
              <TableRow key={version.id}>
                <TableCell>v{version.version_number}</TableCell>
                <TableCell>{statusLabels[version.status]}</TableCell>
                <TableCell>{new Date(version.created_at).toLocaleDateString('uk-UA')}</TableCell>
                <TableCell>{version.approved_at ? new Date(version.approved_at).toLocaleDateString('uk-UA') : ''}</TableCell>
                <TableCell>{version.change_reason}</TableCell>
                <TableCell align="right">
                  <Tooltip title="Архівувати версію">
                    <Button
                      disabled={version.status === 'archived' || archiveVersion.isPending}
                      size="small"
                      onClick={() => archiveVersion.mutate(version.id)}
                    >
                      <DeleteIcon fontSize="small" />
                    </Button>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <VersionSelect label="Початкова версія" value={left} versions={versions.data ?? []} onChange={setLeft} />
          <VersionSelect label="Версія для порівняння" value={right} versions={versions.data ?? []} onChange={setRight} />
        </Stack>
        {compare.data ? (
          <Stack spacing={1} sx={{ mt: 2 }}>
            <Typography>Додано: {compare.data.added.length}</Typography>
            <Typography>Видалено: {compare.data.removed.length}</Typography>
            <Typography>Змінено: {compare.data.changed.length}</Typography>
          </Stack>
        ) : null}
      </Paper>
    </Stack>
  );
}

export function BomPrintPage() {
  const { specificationId = '' } = useParams();
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const spec = useQuery({
    queryKey: ['bom', 'specification', specificationId],
    queryFn: () => getBomSpecification(specificationId),
  });
  const versions = useQuery({
    queryKey: ['bom', 'versions', specificationId],
    queryFn: () => listBomVersions(specificationId),
  });
  const version = versions.data?.find((candidate) => candidate.version_number === spec.data?.current_version_number);
  const preview = useQuery({
    queryKey: ['bom', 'preview', version?.id],
    queryFn: () => fetchBomPreviewHtml(version?.id ?? '', false),
    enabled: Boolean(version?.id),
  });
  const downloadMutation = useMutation({
    mutationFn: (format: 'pdf' | 'xlsx') => downloadBomFile(version?.id ?? '', format),
  });
  const printDocument = () => {
    const frameWindow = iframeRef.current?.contentWindow;
    if (frameWindow) {
      frameWindow.focus();
      frameWindow.print();
      return;
    }
    window.print();
  };
  return (
    <Stack className="bom-print-page" spacing={2}>
      <GlobalStyles
        styles={{
          '@media print': {
            'body *': { visibility: 'hidden' },
            '.bom-print-frame': {
              border: 0,
              height: '100vh',
              left: 0,
              position: 'fixed',
              top: 0,
              visibility: 'visible',
              width: '100vw',
            },
            '.bom-print-actions, .bom-print-heading': { display: 'none !important' },
          },
        }}
      />
      <Stack
        className="bom-print-heading bom-print-actions"
        direction="row"
        flexWrap="wrap"
        gap={1}
        justifyContent="space-between"
      >
        <Typography variant="h4">Попередній перегляд і друк</Typography>
        <Stack direction="row" gap={1}>
          <Button startIcon={<PrintIcon />} variant="contained" onClick={printDocument}>
            Друкувати
          </Button>
          <Button startIcon={<PictureAsPdfIcon />} onClick={() => version && downloadMutation.mutate('pdf')}>
            Завантажити PDF
          </Button>
          <Button startIcon={<TableChartIcon />} onClick={() => version && downloadMutation.mutate('xlsx')}>
            Завантажити Excel
          </Button>
        </Stack>
      </Stack>
      {downloadMutation.isError ? (
        <Alert className="bom-print-actions" severity="error">
          РќРµ РІРґР°Р»РѕСЃСЏ Р·Р°РІР°РЅС‚Р°Р¶РёС‚Рё С„Р°Р№Р». РџРµСЂРµРІС–СЂС‚Рµ РґРѕСЃС‚СѓРї Р°Р±Рѕ СЃРїСЂРѕР±СѓР№С‚Рµ С‰Рµ СЂР°Р·.
        </Alert>
      ) : null}
      {preview.isError ? (
        <Alert severity="error">Не вдалося завантажити попередній перегляд специфікації.</Alert>
      ) : version && preview.data ? (
        <Box
          className="bom-print-frame"
          component="iframe"
          ref={iframeRef}
          srcDoc={preview.data}
          sx={{ bgcolor: '#fff', border: 1, borderColor: 'divider', height: '78vh', width: '100%' }}
          title="Попередній перегляд специфікації"
        />
      ) : version ? (
        <Alert severity="info">Завантаження попереднього перегляду...</Alert>
      ) : (
        <Alert severity="info">Версію для друку ще не знайдено.</Alert>
      )}
    </Stack>
  );
}

function SpecificationDialog({
  loading,
  open,
  organizations,
  onClose,
  onSubmit,
}: {
  loading: boolean;
  open: boolean;
  organizations: Array<{ id: string; name: string }>;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [organizationId, setOrganizationId] = useState('');
  useEffect(() => {
    if (!organizationId && organizations[0]) setOrganizationId(organizations[0].id);
  }, [organizationId, organizations]);
  return (
    <Dialog fullWidth open={open} onClose={onClose}>
      <DialogTitle>Створити специфікацію</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <FormControl fullWidth>
            <InputLabel>Організація</InputLabel>
            <Select label="Організація" value={organizationId} onChange={(event) => setOrganizationId(event.target.value)}>
              {organizations.map((organization) => (
                <MenuItem key={organization.id} value={organization.id}>
                  {organization.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField label="Код специфікації" value={code} onChange={(event) => setCode(event.target.value)} />
          <TextField label="Назва специфікації" value={name} onChange={(event) => setName(event.target.value)} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Скасувати</Button>
        <Button disabled={loading || !code || !name || !organizationId} variant="contained" onClick={() => onSubmit({ code, name, organization_id: organizationId, specification_type: 'product', is_active: true })}>
          Створити
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function CopyDialog({
  loading,
  open,
  source,
  onClose,
  onSubmit,
}: {
  loading: boolean;
  open: boolean;
  source: BomSpecification | null;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const [code, setCode] = useState('');
  useEffect(() => {
    if (source) setCode(`${source.code}-COPY`);
  }, [source]);
  return (
    <Dialog fullWidth open={open} onClose={onClose}>
      <DialogTitle>Копіювати специфікацію</DialogTitle>
      <DialogContent>
        <TextField fullWidth label="Новий код" sx={{ mt: 1 }} value={code} onChange={(event) => setCode(event.target.value)} />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Скасувати</Button>
        <Button disabled={loading || !code} variant="contained" onClick={() => onSubmit({ code })}>
          Копіювати
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function LineDialog({
  items = [],
  mode,
  open,
  units,
  onClose,
  onSubmit,
}: {
  items?: Item[];
  mode: 'manual' | 'inventory';
  open: boolean;
  units: Unit[];
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => void;
}) {
  const [itemId, setItemId] = useState('');
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('1');
  const [unitId, setUnitId] = useState('');
  const [notes, setNotes] = useState('');
  useEffect(() => {
    if (!unitId && units[0]) setUnitId(units[0].id);
  }, [unitId, units]);
  const selectedItem = items.find((item) => item.id === itemId);
  return (
    <Dialog fullWidth open={open} onClose={onClose}>
      <DialogTitle>{mode === 'inventory' ? 'Обрати з номенклатури' : 'Додати вручну'}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          {mode === 'inventory' ? (
            <FormControl fullWidth>
              <InputLabel>Номенклатура</InputLabel>
              <Select label="Номенклатура" value={itemId} onChange={(event) => setItemId(event.target.value)}>
                {items.map((item) => (
                  <MenuItem key={item.id} value={item.id}>
                    {item.sku} · {item.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : null}
          <TextField
            label="Назва позиції"
            value={name || selectedItem?.name || ''}
            onChange={(event) => setName(event.target.value)}
          />
          <Stack direction="row" spacing={2}>
            <TextField label="Кількість" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
            <FormControl fullWidth>
              <InputLabel>Одиниця</InputLabel>
              <Select label="Одиниця" value={unitId || selectedItem?.unit_of_measure_id || ''} onChange={(event) => setUnitId(event.target.value)}>
                {units.map((unit) => (
                  <MenuItem key={unit.id} value={unit.id}>
                    {unit.symbol} · {unit.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          <TextField label="Примітка" multiline minRows={2} value={notes} onChange={(event) => setNotes(event.target.value)} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Скасувати</Button>
        <Button
          variant="contained"
          onClick={() =>
            onSubmit({
              inventory_item_id: mode === 'inventory' ? itemId : null,
              display_name: name || selectedItem?.name,
              quantity,
              unit_of_measure_id: unitId || selectedItem?.unit_of_measure_id,
              position_code: selectedItem?.sku,
              notes,
              source_type: mode === 'inventory' ? 'inventory_item' : 'manual',
            })
          }
        >
          Додати
        </Button>
      </DialogActions>
    </Dialog>
  );
}

function VersionSelect({
  label,
  value,
  versions,
  onChange,
}: {
  label: string;
  value: string;
  versions: BomVersion[];
  onChange: (value: string) => void;
}) {
  return (
    <FormControl fullWidth>
      <InputLabel>{label}</InputLabel>
      <Select label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        {versions.map((version) => (
          <MenuItem key={version.id} value={version.id}>
            v{version.version_number} · {statusLabels[version.status]}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}
