import AddIcon from '@mui/icons-material/Add';
import KeyIcon from '@mui/icons-material/Key';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
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
import type { ApiError } from '../services/apiClient';
import { queryClient } from '../services/queryClient';

export function UsersPage() {
  const { t } = useTranslation(['identity']);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);
  const usersQuery = useQuery({ queryKey: ['identity', 'users'], queryFn: () => identityApi.listUsers() });
  const rolesQuery = useQuery({ queryKey: ['identity', 'roles'], queryFn: () => identityApi.listRoles() });
  const resetMutation = useMutation({
    mutationFn: identityApi.resetUserPassword,
    onSuccess: (response) => setTemporaryPassword(response.temporary_password),
  });

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={2}>
        <Box>
          <Typography variant="h4">{t('users.title')}</Typography>
          <Typography color="text.secondary">{t('users.subtitle')}</Typography>
        </Box>
        <Button startIcon={<AddIcon />} variant="contained" onClick={() => setDialogOpen(true)}>
          {t('users.create')}
        </Button>
      </Stack>
      {temporaryPassword ? (
        <Alert severity="success" onClose={() => setTemporaryPassword(null)}>
          {t('users.temporaryPassword')}: {temporaryPassword}
        </Alert>
      ) : null}
      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('fields.name')}</TableCell>
              <TableCell>{t('fields.email')}</TableCell>
              <TableCell>{t('fields.status')}</TableCell>
              <TableCell>{t('fields.passwordStatus')}</TableCell>
              <TableCell align="right">{t('actions.title')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(usersQuery.data?.items ?? []).map((user) => (
              <TableRow hover key={user.id}>
                <TableCell>{user.display_name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>{user.is_active ? t('values.active') : t('values.inactive')}</TableCell>
                <TableCell>
                  {user.must_change_password ? t('values.mustChange') : t('values.ready')}
                </TableCell>
                <TableCell align="right">
                  <Button
                    disabled={resetMutation.isPending}
                    size="small"
                    startIcon={<KeyIcon />}
                    onClick={() => resetMutation.mutate(user.id)}
                  >
                    {t('actions.resetPassword')}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
      <UserCreateDialog
        open={dialogOpen}
        roles={rolesQuery.data?.items ?? []}
        onClose={() => setDialogOpen(false)}
        onCreated={(password) => {
          setTemporaryPassword(password);
          setDialogOpen(false);
        }}
      />
    </Stack>
  );
}

function UserCreateDialog({
  onClose,
  onCreated,
  open,
  roles,
}: {
  onClose: () => void;
  onCreated: (password: string | null) => void;
  open: boolean;
  roles: { id: string; name: string }[];
}) {
  const { t } = useTranslation(['identity']);
  const [step, setStep] = useState(0);
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [temporaryPassword, setTemporaryPassword] = useState('');
  const [roleIds, setRoleIds] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: identityApi.createUser,
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['identity', 'users'] });
      onCreated(response.temporary_password);
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (step === 0) {
      setStep(1);
      return;
    }
    mutation.mutate({
      display_name: displayName,
      email,
      is_active: true,
      is_superuser: false,
      role_ids: roleIds,
      temporary_password: temporaryPassword || null,
    });
  };

  return (
    <Dialog fullWidth maxWidth="sm" open={open} onClose={onClose}>
      <Box component="form" onSubmit={submit}>
        <DialogTitle>{t('users.create')}</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ pt: 1 }}>
            <Stepper activeStep={step}>
              <Step>
                <StepLabel>{t('users.steps.account')}</StepLabel>
              </Step>
              <Step>
                <StepLabel>{t('users.steps.roles')}</StepLabel>
              </Step>
            </Stepper>
            {mutation.error ? (
              <Alert severity="error">
                {((mutation.error as ApiError).message ?? t('errors.generic'))}
              </Alert>
            ) : null}
            {step === 0 ? (
              <>
                <TextField
                  label={t('fields.name')}
                  required
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                />
                <TextField
                  label={t('fields.email')}
                  required
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <TextField
                  helperText={t('users.passwordHelper')}
                  label={t('fields.temporaryPassword')}
                  type="password"
                  value={temporaryPassword}
                  onChange={(event) => setTemporaryPassword(event.target.value)}
                />
              </>
            ) : (
              <TextField
                select
                SelectProps={{ multiple: true }}
                label={t('fields.roles')}
                value={roleIds}
                onChange={(event) => {
                  const value = event.target.value;
                  setRoleIds(typeof value === 'string' ? value.split(',') : value);
                }}
              >
                {roles.map((role) => (
                  <MenuItem key={role.id} value={role.id}>
                    {role.name}
                  </MenuItem>
                ))}
              </TextField>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          {step === 1 ? <Button onClick={() => setStep(0)}>{t('actions.back')}</Button> : null}
          <Button onClick={onClose}>{t('actions.cancel')}</Button>
          <Button disabled={mutation.isPending} type="submit" variant="contained">
            {step === 0 ? t('actions.next') : t('actions.create')}
          </Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}
