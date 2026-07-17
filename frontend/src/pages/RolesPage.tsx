import AddIcon from '@mui/icons-material/Add';
import ShieldIcon from '@mui/icons-material/Shield';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';

import * as identityApi from '../features/identity/api';
import type { Permission, Role } from '../features/identity/types';
import type { ApiError } from '../services/apiClient';
import { queryClient } from '../services/queryClient';

export function RolesPage() {
  const { t } = useTranslation(['identity']);
  const [createOpen, setCreateOpen] = useState(false);
  const [permissionRole, setPermissionRole] = useState<Role | null>(null);
  const rolesQuery = useQuery({ queryKey: ['identity', 'roles'], queryFn: () => identityApi.listRoles() });
  const permissionsQuery = useQuery({
    queryKey: ['identity', 'permissions'],
    queryFn: identityApi.listPermissions,
  });

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4">{t('roles.title')}</Typography>
          <Typography color="text.secondary">{t('roles.subtitle')}</Typography>
        </Box>
        <Button startIcon={<AddIcon />} variant="contained" onClick={() => setCreateOpen(true)}>
          {t('roles.create')}
        </Button>
      </Stack>
      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('fields.name')}</TableCell>
              <TableCell>{t('fields.code')}</TableCell>
              <TableCell>{t('fields.status')}</TableCell>
              <TableCell align="right">{t('actions.title')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(rolesQuery.data?.items ?? []).map((role) => (
              <TableRow hover key={role.id}>
                <TableCell>
                  <Typography fontWeight={700}>{role.name}</Typography>
                  <Typography color="text.secondary" variant="body2">
                    {role.description}
                  </Typography>
                </TableCell>
                <TableCell>{role.code}</TableCell>
                <TableCell>{role.is_system ? t('values.system') : t('values.custom')}</TableCell>
                <TableCell align="right">
                  <Button
                    disabled={role.is_system}
                    size="small"
                    startIcon={<ShieldIcon />}
                    onClick={() => setPermissionRole(role)}
                  >
                    {t('actions.permissions')}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <RoleCreateDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      <PermissionDialog
        permissions={permissionsQuery.data ?? []}
        role={permissionRole}
        onClose={() => setPermissionRole(null)}
      />
    </Stack>
  );
}

function RoleCreateDialog({ onClose, open }: { onClose: () => void; open: boolean }) {
  const { t } = useTranslation(['identity']);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [description, setDescription] = useState('');
  const mutation = useMutation({
    mutationFn: identityApi.createRole,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['identity', 'roles'] });
      onClose();
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    mutation.mutate({ code, description, name });
  };

  return (
    <Dialog fullWidth maxWidth="sm" open={open} onClose={onClose}>
      <Box component="form" onSubmit={submit}>
        <DialogTitle>{t('roles.create')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {mutation.error ? (
              <Alert severity="error">
                {((mutation.error as ApiError).message ?? t('errors.generic'))}
              </Alert>
            ) : null}
            <TextField label={t('fields.name')} required value={name} onChange={(event) => setName(event.target.value)} />
            <TextField label={t('fields.code')} required value={code} onChange={(event) => setCode(event.target.value)} />
            <TextField
              label={t('fields.description')}
              multiline
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>{t('actions.cancel')}</Button>
          <Button disabled={mutation.isPending} type="submit" variant="contained">
            {t('actions.create')}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}

function PermissionDialog({
  onClose,
  permissions,
  role,
}: {
  onClose: () => void;
  permissions: Permission[];
  role: Role | null;
}) {
  const { t } = useTranslation(['identity']);
  const [selected, setSelected] = useState<string[]>([]);
  const mutation = useMutation({
    mutationFn: () => identityApi.setRolePermissions(role?.id ?? '', selected),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['identity', 'roles'] });
      onClose();
    },
  });

  return (
    <Dialog fullWidth maxWidth="md" open={Boolean(role)} onClose={onClose}>
      <DialogTitle>{t('roles.permissionsTitle', { name: role?.name })}</DialogTitle>
      <DialogContent>
        <Stack spacing={1} sx={{ pt: 1 }}>
          {mutation.error ? (
            <Alert severity="error">{((mutation.error as ApiError).message ?? t('errors.generic'))}</Alert>
          ) : null}
          {permissions.map((permission) => (
            <FormControlLabel
              key={permission.id}
              control={
                <Checkbox
                  checked={selected.includes(permission.id)}
                  onChange={(_, checked) =>
                    setSelected((current) =>
                      checked
                        ? [...current, permission.id]
                        : current.filter((item) => item !== permission.id),
                    )
                  }
                />
              }
              label={`${permission.name} (${permission.code})`}
            />
          ))}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t('actions.cancel')}</Button>
        <Button disabled={mutation.isPending || !role} variant="contained" onClick={() => mutation.mutate()}>
          {t('actions.save')}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
