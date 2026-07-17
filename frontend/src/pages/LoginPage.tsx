import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useAuth } from '../features/identity/AuthContext';
import type { ApiError } from '../services/apiClient';

export function LoginPage() {
  const { t } = useTranslation(['identity']);
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (auth.user && !auth.user.must_change_password) {
    return <Navigate replace to="/" />;
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const user = await auth.login(email, password);
      if (user.must_change_password) {
        navigate('/change-password', { replace: true });
        return;
      }
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
      navigate(from ?? '/', { replace: true });
    } catch (caught) {
      const apiError = caught as ApiError;
      setError(apiError.message ?? t('login.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        alignItems: 'center',
        bgcolor: 'background.default',
        display: 'flex',
        justifyContent: 'center',
        minHeight: '100vh',
        px: 2,
      }}
    >
      <Paper component="form" variant="outlined" sx={{ maxWidth: 420, p: 4, width: '100%' }} onSubmit={submit}>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <LockOutlinedIcon color="primary" />
            <Typography variant="h4">{t('login.title')}</Typography>
            <Typography color="text.secondary">{t('login.subtitle')}</Typography>
          </Stack>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <TextField
            autoComplete="email"
            label={t('fields.email')}
            required
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <TextField
            autoComplete="current-password"
            label={t('fields.password')}
            required
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button disabled={loading} size="large" type="submit" variant="contained">
            {t('login.submit')}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
