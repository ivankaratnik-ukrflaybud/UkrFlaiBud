import PasswordIcon from '@mui/icons-material/Password';
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../features/identity/AuthContext';
import type { ApiError } from '../services/apiClient';

export function ChangePasswordPage() {
  const { t } = useTranslation(['identity']);
  const auth = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirmation) {
      setError(t('changePassword.mismatch'));
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await auth.updatePassword(currentPassword, newPassword);
      navigate('/', { replace: true });
    } catch (caught) {
      const apiError = caught as ApiError;
      setError(apiError.message ?? t('changePassword.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center' }}>
      <Paper component="form" variant="outlined" sx={{ maxWidth: 520, p: 4, width: '100%' }} onSubmit={submit}>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <PasswordIcon color="primary" />
            <Typography variant="h4">{t('changePassword.title')}</Typography>
            <Typography color="text.secondary">{t('changePassword.subtitle')}</Typography>
          </Stack>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <TextField
            autoComplete="current-password"
            label={t('fields.currentPassword')}
            required
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
          />
          <TextField
            autoComplete="new-password"
            helperText={t('changePassword.helper')}
            label={t('fields.newPassword')}
            required
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
          <TextField
            autoComplete="new-password"
            label={t('fields.confirmPassword')}
            required
            type="password"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
          <Button disabled={loading} size="large" type="submit" variant="contained">
            {t('changePassword.submit')}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
