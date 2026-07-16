import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';

import enCalendar from '../locales/en/calendar.json';
import enCommon from '../locales/en/common.json';
import enDashboard from '../locales/en/dashboard.json';
import enOrganizations from '../locales/en/organizations.json';
import enSettings from '../locales/en/settings.json';
import enTasks from '../locales/en/tasks.json';
import enUsers from '../locales/en/users.json';
import ukCalendar from '../locales/uk/calendar.json';
import ukCommon from '../locales/uk/common.json';
import ukDashboard from '../locales/uk/dashboard.json';
import ukOrganizations from '../locales/uk/organizations.json';
import ukSettings from '../locales/uk/settings.json';
import ukTasks from '../locales/uk/tasks.json';
import ukUsers from '../locales/uk/users.json';

export const defaultLocale = import.meta.env.VITE_DEFAULT_LOCALE ?? 'uk-UA';

void i18next.use(initReactI18next).init({
  fallbackLng: 'uk-UA',
  lng: defaultLocale,
  ns: ['common', 'dashboard', 'tasks', 'users', 'calendar', 'settings', 'organizations'],
  defaultNS: 'common',
  interpolation: {
    escapeValue: false,
  },
  resources: {
    'uk-UA': {
      calendar: ukCalendar,
      common: ukCommon,
      dashboard: ukDashboard,
      organizations: ukOrganizations,
      settings: ukSettings,
      tasks: ukTasks,
      users: ukUsers,
    },
    en: {
      calendar: enCalendar,
      common: enCommon,
      dashboard: enDashboard,
      organizations: enOrganizations,
      settings: enSettings,
      tasks: enTasks,
      users: enUsers,
    },
  },
});

export { i18next };
