import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1c605c',
    },
    secondary: {
      main: '#be392c',
    },
    background: {
      default: '#f5f7f4',
      paper: '#ffffff',
    },
    text: {
      primary: '#17202a',
      secondary: '#52606d',
    },
  },
  shape: {
    borderRadius: 6,
  },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontSize: 'clamp(2.2rem, 5vw, 4.75rem)',
      fontWeight: 800,
      lineHeight: 0.98,
    },
  },
});

