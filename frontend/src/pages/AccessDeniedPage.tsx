import BlockIcon from '@mui/icons-material/Block';
import { Button, Paper, Stack, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink } from 'react-router-dom';

export function AccessDeniedPage() {
  const { t } = useTranslation(['identity']);

  return (
    <Paper variant="outlined" sx={{ p: 4 }}>
      <Stack spacing={2}>
        <BlockIcon color="error" />
        <Typography variant="h4">{t('accessDenied.title')}</Typography>
        <Typography color="text.secondary">{t('accessDenied.description')}</Typography>
        <Button component={RouterLink} sx={{ alignSelf: 'flex-start' }} to="/" variant="contained">
          {t('accessDenied.back')}
        </Button>
      </Stack>
    </Paper>
  );
}
