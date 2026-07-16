import dayjs from 'dayjs';
import 'dayjs/locale/uk';
import localizedFormat from 'dayjs/plugin/localizedFormat';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import updateLocale from 'dayjs/plugin/updateLocale';

dayjs.extend(localizedFormat);
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(updateLocale);
dayjs.locale('uk');
dayjs.updateLocale('uk', {
  weekStart: 1,
});
dayjs.tz.setDefault(import.meta.env.VITE_TIMEZONE ?? 'Europe/Kyiv');

export const localeConfig = {
  defaultLocale: import.meta.env.VITE_DEFAULT_LOCALE ?? 'uk-UA',
  timezone: import.meta.env.VITE_TIMEZONE ?? 'Europe/Kyiv',
  dateFormat: 'DD.MM.YYYY',
  timeFormat: 'HH:mm',
  firstDayOfWeek: 1,
} as const;

export { dayjs };

