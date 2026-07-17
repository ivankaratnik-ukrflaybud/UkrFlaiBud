import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Resolver, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { zodResolver } from '@hookform/resolvers/zod';

import { queryClient } from '../../services/queryClient';
import { createEntity, deleteEntity, EntityKind, listEntities, updateEntity } from './api';
import { pageConfigs } from './config';
import { EntityFilterControl, EntityFormControl } from './OrganizationControls';
import type { ApiError, OrganizationEntity, SortDirection } from './types';
import {
  buildDepartmentTree,
  formatValue,
  formValuesFor,
  normalizePayload,
  schemaFor,
  type FormValues,
} from './utils';

export function OrganizationCorePage({ kind }: { kind: EntityKind }) {
  const config = pageConfigs[kind];
  const { t } = useTranslation(['common', 'organizations']);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState(config.defaultSort);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [filters, setFilters] = useState<Record<string, string | boolean>>({});
  const [editing, setEditing] = useState<OrganizationEntity | null>(null);
  const [viewing, setViewing] = useState<OrganizationEntity | null>(null);
  const [deleting, setDeleting] = useState<OrganizationEntity | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const listQuery = useQuery({
    queryKey: [kind, page, pageSize, sortBy, sortDirection, filters],
    queryFn: () =>
      listEntities(kind, {
        filters,
        page: page + 1,
        pageSize,
        sortBy,
        sortDirection,
      }),
  });
  const organizationsQuery = useLookupQuery('organizations');
  const departmentsQuery = useLookupQuery('departments');
  const positionsQuery = useLookupQuery('positions');
  const employeesQuery = useLookupQuery('employees');

  const mutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = normalizePayload(config, values, editing);
      if (editing) {
        return updateEntity(kind, editing.id, payload);
      }
      return createEntity(kind, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: [kind] });
      closeForm();
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (entity: OrganizationEntity) => deleteEntity(kind, entity.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: [kind] });
      setDeleting(null);
    },
  });

  const formSchema = useMemo(() => schemaFor(config, t), [config, t]);
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema) as Resolver<FormValues>,
    values: formValuesFor(config, editing),
  });

  const items = listQuery.data?.items ?? [];
  const departmentTree = useMemo(
    () => buildDepartmentTree(departmentsQuery.data?.items ?? []),
    [departmentsQuery.data?.items],
  );

  const openCreate = () => {
    setEditing(null);
    setDrawerOpen(true);
  };
  const openEdit = (entity: OrganizationEntity) => {
    setEditing(entity);
    setDrawerOpen(true);
  };
  const closeForm = () => {
    setDrawerOpen(false);
    setEditing(null);
    mutation.reset();
  };
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setSortDirection('asc');
    }
  };

  return (
    <Stack spacing={3}>
      <Toolbar disableGutters sx={{ justifyContent: 'space-between', gap: 2 }}>
        <Box>
          <Typography variant="h4">{t(config.titleKey)}</Typography>
          <Typography color="text.secondary">{t('organizations:moduleSubtitle')}</Typography>
        </Box>
        <Button startIcon={<AddIcon />} variant="contained" onClick={openCreate}>
          {t(config.createKey)}
        </Button>
      </Toolbar>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: { xs: '1fr', md: 'repeat(4, minmax(0, 1fr))' },
          }}
        >
          {config.filters.map((field) => (
            <EntityFilterControl
              key={field.name}
              field={field}
              value={filters[field.name]}
              organizations={organizationsQuery.data?.items ?? []}
              departments={departmentsQuery.data?.items ?? []}
              positions={positionsQuery.data?.items ?? []}
              employees={employeesQuery.data?.items ?? []}
              onChange={(value) => {
                setPage(0);
                setFilters((current) => ({ ...current, [field.name]: value }));
              }}
            />
          ))}
        </Box>
      </Paper>

      {mutation.error ? <ErrorAlert error={mutation.error as unknown as ApiError} /> : null}
      {listQuery.error ? <ErrorAlert error={listQuery.error as unknown as ApiError} /> : null}

      {kind === 'departments' ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography fontWeight={800}>{t('organizations:departmentTree')}</Typography>
          <List dense>
            {departmentTree.length === 0 ? (
              <ListItem>
                <ListItemText primary={t('organizations:emptyState')} />
              </ListItem>
            ) : (
              departmentTree.map((node) => (
                <ListItem key={node.department.id} sx={{ pl: 2 + node.depth * 3 }}>
                  <ListItemText primary={node.department.name} secondary={node.department.code} />
                </ListItem>
              ))
            )}
          </List>
        </Paper>
      ) : null}

      <Paper variant="outlined">
        {listQuery.isLoading ? (
          <Stack alignItems="center" sx={{ py: 6 }}>
            <CircularProgress />
          </Stack>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {config.columns.map((column) => (
                    <TableCell key={column}>
                      <TableSortLabel
                        active={sortBy === column}
                        direction={sortBy === column ? sortDirection : 'asc'}
                        onClick={() => handleSort(column)}
                      >
                        {t(`organizations:fields.${column}`)}
                      </TableSortLabel>
                    </TableCell>
                  ))}
                  <TableCell align="right">{t('organizations:actions.title')}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={config.columns.length + 1}>
                      <Typography color="text.secondary" sx={{ py: 3, textAlign: 'center' }}>
                        {t('organizations:emptyState')}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  items.map((entity) => (
                    <TableRow hover key={entity.id}>
                      {config.columns.map((column) => (
                        <TableCell key={column}>
                          {formatValue(column, entity, {
                            departments: departmentsQuery.data?.items ?? [],
                            employees: employeesQuery.data?.items ?? [],
                            organizations: organizationsQuery.data?.items ?? [],
                            positions: positionsQuery.data?.items ?? [],
                            t,
                          })}
                        </TableCell>
                      ))}
                      <TableCell align="right">
                        <Tooltip title={t('organizations:actions.view')}>
                          <IconButton onClick={() => setViewing(entity)}>
                            <VisibilityIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t('organizations:actions.edit')}>
                          <IconButton onClick={() => openEdit(entity)}>
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t('organizations:actions.delete')}>
                          <IconButton color="error" onClick={() => setDeleting(entity)}>
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        <TablePagination
          component="div"
          count={listQuery.data?.total ?? 0}
          labelRowsPerPage={t('organizations:pagination.rowsPerPage')}
          page={page}
          rowsPerPage={pageSize}
          rowsPerPageOptions={[10, 25, 50]}
          onPageChange={(_, nextPage) => setPage(nextPage)}
          onRowsPerPageChange={(event) => {
            setPageSize(Number(event.target.value));
            setPage(0);
          }}
        />
      </Paper>

      <Drawer anchor="right" open={drawerOpen} onClose={closeForm}>
        <Box component="form" sx={{ width: { xs: 320, sm: 520 }, p: 3 }} onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <Stack spacing={2}>
            <Typography variant="h5">
              {editing ? t('organizations:actions.edit') : t(config.createKey)}
            </Typography>
            {config.fields.map((field) => (
              <EntityFormControl
                key={field.name}
                control={form.control}
                errors={form.formState.errors}
                field={field}
                register={form.register}
                organizations={organizationsQuery.data?.items ?? []}
                departments={departmentsQuery.data?.items ?? []}
                positions={positionsQuery.data?.items ?? []}
                employees={employeesQuery.data?.items ?? []}
              />
            ))}
            <Stack direction="row" justifyContent="flex-end" spacing={1}>
              <Button onClick={closeForm}>{t('common:actions.cancel')}</Button>
              <Button disabled={mutation.isPending} type="submit" variant="contained">
                {t('common:actions.save')}
              </Button>
            </Stack>
          </Stack>
        </Box>
      </Drawer>

      <Drawer anchor="right" open={Boolean(viewing)} onClose={() => setViewing(null)}>
        <Box sx={{ width: { xs: 320, sm: 520 }, p: 3 }}>
          <Stack spacing={2}>
            <Typography variant="h5">{t('organizations:actions.view')}</Typography>
            {viewing
              ? [...config.columns, 'created_at', 'updated_at'].map((field) => (
                  <Box key={field}>
                    <Typography color="text.secondary" variant="caption">
                      {t(`organizations:fields.${field}`)}
                    </Typography>
                    <Typography>
                      {formatValue(field, viewing, {
                        departments: departmentsQuery.data?.items ?? [],
                        employees: employeesQuery.data?.items ?? [],
                        organizations: organizationsQuery.data?.items ?? [],
                        positions: positionsQuery.data?.items ?? [],
                        t,
                      })}
                    </Typography>
                  </Box>
                ))
              : null}
          </Stack>
        </Box>
      </Drawer>

      <Dialog open={Boolean(deleting)} onClose={() => setDeleting(null)}>
        <DialogTitle>{t('organizations:deleteDialog.title')}</DialogTitle>
        <DialogContent>
          <Typography>{t('organizations:deleteDialog.description')}</Typography>
          {deleteMutation.error ? (
            <ErrorAlert error={deleteMutation.error as unknown as ApiError} />
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleting(null)}>{t('common:actions.cancel')}</Button>
          <Button
            color="error"
            disabled={!deleting || deleteMutation.isPending}
            variant="contained"
            onClick={() => deleting && deleteMutation.mutate(deleting)}
          >
            {t('organizations:actions.delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

function useLookupQuery<K extends EntityKind>(kind: K) {
  return useQuery({
    queryKey: [kind, 'lookup'],
    queryFn: () =>
      listEntities(kind, {
        filters: {},
        page: 1,
        pageSize: 100,
        sortBy: kind === 'employees' ? 'last_name' : 'name',
        sortDirection: 'asc',
      }),
  });
}

function ErrorAlert({ error }: { error: ApiError }) {
  const { t } = useTranslation(['organizations']);
  return <Alert severity="error">{error.message ?? t('errors.generic')}</Alert>;
}
