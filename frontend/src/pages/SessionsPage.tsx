import LogoutIcon from '@mui/icons-material/Logout';
import { Button, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from '@mui/material';
import { useMutation, useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { useTranslation } from 'react-i18next';

import * as identityApi from '../features/identity/api';
import { queryClient } from '../services/queryClient';

export function SessionsPage() {
  const { t } = useTranslation(['identity']);
  const sessionsQuery = useQuery({
    queryKey: ['identity', 'sessions'],
    queryFn: identityApi.listOwnSessions,
  });
  const revokeMutation = useMutation({
    mutationFn: identityApi.revokeOwnSession,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['identity', 'sessions'] }),
  });

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4">{t('sessions.title')}</Typography>
        <Typography color="text.secondary">{t('sessions.subtitle')}</Typography>
      </Stack>
      <Paper variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t('fields.device')}</TableCell>
              <TableCell>{t('fields.ipAddress')}</TableCell>
              <TableCell>{t('fields.lastUsed')}</TableCell>
              <TableCell>{t('fields.expiresAt')}</TableCell>
              <TableCell align="right">{t('actions.title')}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(sessionsQuery.data ?? []).map((session) => (
              <TableRow hover key={session.id}>
                <TableCell>{session.device_name ?? t('values.unknownDevice')}</TableCell>
                <TableCell>{session.ip_address ?? t('values.empty')}</TableCell>
                <TableCell>{dayjs(session.last_used_at).format('DD.MM.YYYY HH:mm')}</TableCell>
                <TableCell>{dayjs(session.expires_at).format('DD.MM.YYYY HH:mm')}</TableCell>
                <TableCell align="right">
                  <Button
                    disabled={Boolean(session.revoked_at) || revokeMutation.isPending}
                    size="small"
                    startIcon={<LogoutIcon />}
                    onClick={() => revokeMutation.mutate(session.id)}
                  >
                    {session.revoked_at ? t('values.revoked') : t('actions.revoke')}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  );
}
