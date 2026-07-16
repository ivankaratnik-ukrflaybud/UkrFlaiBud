import BusinessIcon from '@mui/icons-material/Business';
import { Box, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';

export function AppLogo() {
  const { t } = useTranslation('common');

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
      <Box
        aria-hidden="true"
        sx={{
          alignItems: 'center',
          bgcolor: 'primary.main',
          color: 'primary.contrastText',
          display: 'grid',
          height: 40,
          placeItems: 'center',
          width: 40,
        }}
      >
        <BusinessIcon fontSize="small" />
      </Box>
      <Box>
        <Typography variant="subtitle1" fontWeight={800} lineHeight={1.1}>
          UKRFLYBUD
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t('app.name')}
        </Typography>
      </Box>
    </Box>
  );
}

