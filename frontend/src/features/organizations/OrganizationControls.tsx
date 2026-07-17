import { Checkbox, FormControlLabel, MenuItem, TextField } from '@mui/material';
import { Controller, type UseFormReturn } from 'react-hook-form';
import { useTranslation } from 'react-i18next';

import { employeeStatuses, emptyOption, type FieldConfig, type FieldType } from './config';
import type { Department, Employee, Organization, Position } from './types';
import type { FormValues } from './utils';

interface LookupProps {
  departments: Department[];
  employees: Employee[];
  organizations: Organization[];
  positions: Position[];
}

export function EntityFormControl({
  control,
  departments,
  employees,
  errors,
  field,
  organizations,
  positions,
  register,
}: LookupProps & {
  control: UseFormReturn<FormValues>['control'];
  errors: UseFormReturn<FormValues>['formState']['errors'];
  field: FieldConfig;
  register: UseFormReturn<FormValues>['register'];
}) {
  const { t } = useTranslation(['common', 'organizations']);
  const label = t(`organizations:fields.${field.name}`);
  if (field.type === 'boolean') {
    return (
      <Controller
        control={control}
        name={field.name}
        render={({ field: controllerField }) => (
          <FormControlLabel
            control={
              <Checkbox
                checked={Boolean(controllerField.value)}
                onChange={(_, checked) => controllerField.onChange(checked)}
              />
            }
            label={label}
          />
        )}
      />
    );
  }

  const options = optionsFor(field.type, { departments, employees, organizations, positions, t });
  return (
    <TextField
      select={options.length > 0}
      error={Boolean(errors[field.name])}
      helperText={errors[field.name]?.message as string | undefined}
      label={label}
      multiline={field.multiline}
      rows={field.multiline ? 3 : undefined}
      type={field.type === 'date' ? 'date' : 'text'}
      InputLabelProps={field.type === 'date' ? { shrink: true } : undefined}
      {...register(field.name)}
    >
      {options.map((option) => (
        <MenuItem key={option.value} value={option.value}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );
}

export function EntityFilterControl({
  departments,
  employees,
  field,
  onChange,
  organizations,
  positions,
  value,
}: LookupProps & {
  field: FieldConfig;
  onChange: (value: string | boolean) => void;
  value: string | boolean | undefined;
}) {
  const { t } = useTranslation(['organizations']);
  const label = t(`fields.${field.name}`);
  if (field.type === 'boolean') {
    return (
      <TextField
        select
        label={label}
        value={value === undefined ? emptyOption : String(value)}
        onChange={(event) => onChange(event.target.value === emptyOption ? emptyOption : event.target.value === 'true')}
      >
        <MenuItem value={emptyOption}>{t('filters.all')}</MenuItem>
        <MenuItem value="true">{t('values.active')}</MenuItem>
        <MenuItem value="false">{t('values.inactive')}</MenuItem>
      </TextField>
    );
  }
  const options = optionsFor(field.type, { departments, employees, organizations, positions, t });
  return (
    <TextField
      select={options.length > 0}
      label={label}
      value={value ?? emptyOption}
      onChange={(event) => onChange(event.target.value)}
    >
      {options.length > 0
        ? options.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))
        : null}
    </TextField>
  );
}

function optionsFor(
  type: FieldType,
  lookups: LookupProps & { t: (key: string) => string },
): { label: string; value: string }[] {
  const empty = { label: lookups.t('filters.all'), value: emptyOption };
  if (type === 'organization') {
    return [empty, ...lookups.organizations.map((item) => ({ label: item.name, value: item.id }))];
  }
  if (type === 'department') {
    return [empty, ...lookups.departments.map((item) => ({ label: item.name, value: item.id }))];
  }
  if (type === 'position') {
    return [empty, ...lookups.positions.map((item) => ({ label: item.name, value: item.id }))];
  }
  if (type === 'employee') {
    return [
      empty,
      ...lookups.employees.map((item) => ({
        label: `${item.last_name} ${item.first_name}`,
        value: item.id,
      })),
    ];
  }
  if (type === 'status') {
    return [empty, ...employeeStatuses.map((status) => ({ label: lookups.t(`statuses.${status}`), value: status }))];
  }
  return [];
}
