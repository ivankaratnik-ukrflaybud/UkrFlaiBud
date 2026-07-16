import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import './services/i18n';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

