import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
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
  TextField,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';
import { Controller, Resolver, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import { queryClient } from '../../services/queryClient';
import { createEntity, deleteEntity, EntityKind, listEntities, updateEntity } from './api';
import type {
  ApiError,
  Department,
  Employee,
  EmployeeStatus,
  Organization,
  OrganizationEntity,
  Position,
  SortDirection,
} from './types';

type FieldType = 'text' | 'email' | 'date' | 'boolean' | 'organization' | 'department' | 'position' | 'employee' | 'status';

interface FieldConfig {
  name: string;
  type: FieldType;
  required?: boolean;
  multiline?: boolean;
}

interface PageConfig {
  kind: EntityKind;
  titleKey: string;
  createKey: string;
  fields: FieldConfig[];
  columns: string[];
  filters: FieldConfig[];
  defaultSort: string;
}

type FormValues = Record<string, string | boolean>;

const emptyOption = '';

const pageConfigs: Record<EntityKind, PageConfig> = {
  organizations: {
    kind: 'organizations',
    titleKey: 'organizations:pages.organizations',
    createKey: 'organizations:actions.createOrganization',
    defaultSort: 'name',
    fields: [
      { name: 'name', type: 'text', required: true },
      { name: 'short_name', type: 'text', required: true },
      { name: 'legal_name', type: 'text', required: true },
      { name: 'edrpou', type: 'text', required: true },
      { name: 'tax_number', type: 'text' },
      { name: 'email', type: 'email' },
      { name: 'phone', type: 'text' },
      { name: 'website', type: 'text' },
      { name: 'address', type: 'text', multiline: true },
      { name: 'is_active', type: 'boolean' },
    ],
    columns: ['name', 'short_name', 'edrpou', 'is_active', 'version'],
    filters: [
      { name: 'name', type: 'text' },
      { name: 'edrpou', type: 'text' },
      { name: 'is_active', type: 'boolean' },
    ],
  },
  departments: {
    kind: 'departments',
    titleKey: 'organizations:pages.departments',
    createKey: 'organizations:actions.createDepartment',
    defaultSort: 'name',
    fields: [
      { name: 'organization_id', type: 'organization', required: true },
      { name: 'parent_department_id', type: 'department' },
      { name: 'name', type: 'text', required: true },
      { name: 'code', type: 'text' },
      { name: 'description', type: 'text', multiline: true },
      { name: 'manager_employee_id', type: 'employee' },
      { name: 'is_active', type: 'boolean' },
    ],
    columns: ['name', 'code', 'organization_id', 'parent_department_id', 'is_active', 'version'],
    filters: [
      { name: 'organization_id', type: 'organization' },
      { name: 'parent_department_id', type: 'department' },
      { name: 'name', type: 'text' },
      { name: 'code', type: 'text' },
      { name: 'is_active', type: 'boolean' },
    ],
  },
  positions: {
    kind: 'positions',
    titleKey: 'organizations:pages.positions',
    createKey: 'organizations:actions.createPosition',
    defaultSort: 'name',
    fields: [
      { name: 'organization_id', type: 'organization', required: true },
      { name: 'department_id', type: 'department' },
      { name: 'name', type: 'text', required: true },
      { name: 'code', type: 'text' },
      { name: 'description', type: 'text', multiline: true },
      { name: 'is_active', type: 'boolean' },
    ],
    columns: ['name', 'code', 'organization_id', 'department_id', 'is_active', 'version'],
    filters: [
      { name: 'organization_id', type: 'organization' },
      { name: 'department_id', type: 'department' },
      { name: 'name', type: 'text' },
      { name: 'code', type: 'text' },
      { name: 'is_active', type: 'boolean' },
    ],
  },
  employees: {
    kind: 'employees',
    titleKey: 'organizations:pages.employees',
    createKey: 'organizations:actions.createEmployee',
    defaultSort: 'last_name',
    fields: [
      { name: 'organization_id', type: 'organization', required: true },
      { name: 'department_id', type: 'department' },
      { name: 'position_id', type: 'position' },
      { name: 'personnel_number', type: 'text' },
      { name: 'first_name', type: 'text', required: true },
      { name: 'last_name', type: 'text', required: true },
      { name: 'middle_name', type: 'text' },
      { name: 'email', type: 'email' },
      { name: 'phone', type: 'text' },
      { name: 'hire_date', type: 'date' },
      { name: 'termination_date', type: 'date' },
      { name: 'status', type: 'status', required: true },
      { name: 'supervisor_employee_id', type: 'employee' },
      { name: 'notes', type: 'text', multiline: true },
    ],
    columns: ['last_name', 'first_name', 'personnel_number', 'department_id', 'status', 'version'],
    filters: [
      { name: 'organization_id', type: 'organization' },
      { name: 'department_id', type: 'department' },
      { name: 'position_id', type: 'position' },
      { name: 'supervisor_employee_id', type: 'employee' },
      { name: 'status', type: 'status' },
      { name: 'name', type: 'text' },
    ],
  },
};

const employeeStatuses: EmployeeStatus[] = ['active', 'on_leave', 'terminated'];

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
            <FilterControl
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
              <FormControl
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

function FormControl({
  control,
  departments,
  employees,
  errors,
  field,
  organizations,
  positions,
  register,
}: {
  control: ReturnType<typeof useForm<FormValues>>['control'];
  departments: Department[];
  employees: Employee[];
  errors: ReturnType<typeof useForm<FormValues>>['formState']['errors'];
  field: FieldConfig;
  organizations: Organization[];
  positions: Position[];
  register: ReturnType<typeof useForm<FormValues>>['register'];
}) {
  const { t } = useTranslation(['common', 'organizations']);
  const label = t(`organizations:fields.${field.name}`);
  if (field.type === 'boolean') {
    return (
      <Controller
        control={control}
        name={field.name}
        render={({ field: controllerField }) => (
          <FormControlLabel
            control={<Checkbox checked={Boolean(controllerField.value)} onChange={(_, checked) => controllerField.onChange(checked)} />}
            label={label}
          />
        )}
      />
    );
  }

  const options = optionsFor(field.type, { departments, employees, organizations, positions, t });
  return (
    <TextField
      select={options.length > 0}
      error={Boolean(errors[field.name])}
      helperText={errors[field.name]?.message as string | undefined}
      label={label}
      multiline={field.multiline}
      rows={field.multiline ? 3 : undefined}
      type={field.type === 'date' ? 'date' : 'text'}
      InputLabelProps={field.type === 'date' ? { shrink: true } : undefined}
      {...register(field.name)}
    >
      {options.map((option) => (
        <MenuItem key={option.value} value={option.value}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );
}

function FilterControl({
  departments,
  employees,
  field,
  onChange,
  organizations,
  positions,
  value,
}: {
  departments: Department[];
  employees: Employee[];
  field: FieldConfig;
  onChange: (value: string | boolean) => void;
  organizations: Organization[];
  positions: Position[];
  value: string | boolean | undefined;
}) {
  const { t } = useTranslation(['organizations']);
  const label = t(`fields.${field.name}`);
  if (field.type === 'boolean') {
    return (
      <TextField
        select
        label={label}
        value={value === undefined ? emptyOption : String(value)}
        onChange={(event) => onChange(event.target.value === emptyOption ? emptyOption : event.target.value === 'true')}
      >
        <MenuItem value={emptyOption}>{t('filters.all')}</MenuItem>
        <MenuItem value="true">{t('values.active')}</MenuItem>
        <MenuItem value="false">{t('values.inactive')}</MenuItem>
      </TextField>
    );
  }
  const options = optionsFor(field.type, { departments, employees, organizations, positions, t });
  return (
    <TextField
      select={options.length > 0}
      label={label}
      value={value ?? emptyOption}
      onChange={(event) => onChange(event.target.value)}
    >
      {options.length > 0
        ? options.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))
        : null}
    </TextField>
  );
}

function ErrorAlert({ error }: { error: ApiError }) {
  const { t } = useTranslation(['organizations']);
  return <Alert severity="error">{error.message ?? t('errors.generic')}</Alert>;
}

function optionsFor(
  type: FieldType,
  lookups: {
    departments: Department[];
    employees: Employee[];
    organizations: Organization[];
    positions: Position[];
    t: (key: string) => string;
  },
): { label: string; value: string }[] {
  const empty = { label: lookups.t('filters.all'), value: emptyOption };
  if (type === 'organization') {
    return [empty, ...lookups.organizations.map((item) => ({ label: item.name, value: item.id }))];
  }
  if (type === 'department') {
    return [empty, ...lookups.departments.map((item) => ({ label: item.name, value: item.id }))];
  }
  if (type === 'position') {
    return [empty, ...lookups.positions.map((item) => ({ label: item.name, value: item.id }))];
  }
  if (type === 'employee') {
    return [
      empty,
      ...lookups.employees.map((item) => ({
        label: `${item.last_name} ${item.first_name}`,
        value: item.id,
      })),
    ];
  }
  if (type === 'status') {
    return [empty, ...employeeStatuses.map((status) => ({ label: lookups.t(`statuses.${status}`), value: status }))];
  }
  return [];
}

function schemaFor(config: PageConfig, t: (key: string) => string) {
  const shape: Record<string, z.ZodTypeAny> = {};
  config.fields.forEach((field) => {
    if (field.type === 'boolean') {
      shape[field.name] = z.boolean();
      return;
    }
    if (field.type === 'email') {
      shape[field.name] = field.required
        ? z.string().min(1, t('common:validation.required')).email(t('common:validation.invalidEmail'))
        : z.union([z.string().email(t('common:validation.invalidEmail')), z.literal(''), z.undefined()]);
      return;
    }
    shape[field.name] = field.required
      ? z.string().min(1, t('common:validation.required'))
      : z.string().optional();
  });
  return z.object(shape);
}

function formValuesFor(config: PageConfig, entity: OrganizationEntity | null): FormValues {
  return Object.fromEntries(
    config.fields.map((field) => {
      if (field.type === 'boolean') {
        return [field.name, entity ? Boolean(valueFor(entity, field.name)) : true];
      }
      return [field.name, entity ? String(valueFor(entity, field.name) ?? emptyOption) : emptyOption];
    }),
  );
}

function normalizePayload(
  config: PageConfig,
  values: FormValues,
  editing: OrganizationEntity | null,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  config.fields.forEach((field) => {
    const value = values[field.name];
    payload[field.name] = value === emptyOption && !field.required ? null : value;
  });
  if (editing) {
    payload.version = editing.version;
  }
  return payload;
}

function valueFor(entity: OrganizationEntity, field: string): unknown {
  return (entity as unknown as Record<string, unknown>)[field];
}

function formatValue(
  field: string,
  entity: OrganizationEntity,
  lookups: {
    departments: Department[];
    employees: Employee[];
    organizations: Organization[];
    positions: Position[];
    t: (key: string) => string;
  },
) {
  const value = valueFor(entity, field);
  if (value === null || value === undefined || value === '') {
    return lookups.t('organizations:values.empty');
  }
  if (field === 'is_active') {
    return value ? lookups.t('organizations:values.active') : lookups.t('organizations:values.inactive');
  }
  if (field === 'status') {
    return lookups.t(`organizations:statuses.${value}`);
  }
  if (field.endsWith('_at') || field.endsWith('_date')) {
    return dayjs(String(value)).format('DD.MM.YYYY');
  }
  if (field === 'organization_id') {
    return lookups.organizations.find((item) => item.id === value)?.name ?? String(value);
  }
  if (field === 'department_id' || field === 'parent_department_id') {
    return lookups.departments.find((item) => item.id === value)?.name ?? String(value);
  }
  if (field === 'position_id') {
    return lookups.positions.find((item) => item.id === value)?.name ?? String(value);
  }
  if (field === 'supervisor_employee_id' || field === 'manager_employee_id') {
    const employee = lookups.employees.find((item) => item.id === value);
    return employee ? `${employee.last_name} ${employee.first_name}` : String(value);
  }
  return String(value);
}

function buildDepartmentTree(departments: Department[]) {
  const children = new Map<string | null, Department[]>();
  departments.forEach((department) => {
    const key = department.parent_department_id;
    children.set(key, [...(children.get(key) ?? []), department]);
  });
  const nodes: { department: Department; depth: number }[] = [];
  const visit = (parentId: string | null, depth: number) => {
    (children.get(parentId) ?? []).forEach((department) => {
      nodes.push({ department, depth });
      visit(department.id, depth + 1);
    });
  };
  visit(null, 0);
  return nodes;
}
