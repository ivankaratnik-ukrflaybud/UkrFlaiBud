import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import StorageIcon from '@mui/icons-material/Storage';
import WebhookIcon from '@mui/icons-material/Webhook';
import { Box, Chip, Paper, Stack, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';

import { localeConfig } from '../services/locale';

const preparedAreas = ['projects', 'procurement', 'inventory', 'warehouse', 'accounting', 'crm', 'hr'];

export function DashboardPage() {
  const { t } = useTranslation(['common', 'dashboard']);

  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: { xs: 3, md: 5 } }}>
        <Stack spacing={2}>
          <Chip
            color="primary"
            icon={<CheckCircleIcon />}
            label={t('common:status.infrastructureReady')}
            sx={{ alignSelf: 'flex-start' }}
          />
          <Typography variant="h1">{t('dashboard:title')}</Typography>
          <Typography color="text.secondary" maxWidth="720px" variant="body1">
            {t('dashboard:subtitle')}
          </Typography>
        </Stack>
      </Paper>

      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' },
        }}
      >
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Stack spacing={1}>
            <WebhookIcon color="primary" />
            <Typography fontWeight={800}>{t('dashboard:api.title')}</Typography>
            <Typography color="text.secondary">{t('dashboard:api.description')}</Typography>
          </Stack>
        </Paper>
        <Paper variant="outlined" sx={{ p: 3 }}>
          <Stack spacing={1}>
            <StorageIcon color="primary" />
            <Typography fontWeight={800}>{t('dashboard:database.title')}</Typography>
            <Typography color="text.secondary">{t('dashboard:database.description')}</Typography>
          </Stack>
        </Paper>
      </Box>

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography fontWeight={800}>{t('dashboard:modules.title')}</Typography>
          <Stack direction="row" flexWrap="wrap" gap={1}>
            {preparedAreas.map((area) => (
              <Chip key={area} label={t(`dashboard:modules.items.${area}`)} variant="outlined" />
            ))}
          </Stack>
          <Typography color="text.secondary" variant="body2">
            {t('dashboard:localeSummary', {
              locale: localeConfig.defaultLocale,
              timezone: localeConfig.timezone,
            })}
          </Typography>
        </Stack>
      </Paper>
    </Stack>
  );
}

