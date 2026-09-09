import type { CheckDefinition, CheckOperator, CheckValue } from '../data/types';
import { DATE_OPERATOR_LABEL, OPERATOR_LABEL } from '../data/checks';
import { compact, dateShort, duration, int } from './format';

/* Rendering a check's value is one job in two places — the chip and the
   drawer's pass/fail readout — so the mapping lives here rather than being
   written twice. */

export function formatCheckValue(def: CheckDefinition, value: CheckValue): string {
  const n = Number(value);
  switch (def.valueType) {
    case 'currency':
      return `${n < 0 ? '−' : ''}$${compact(Math.abs(Math.round(n)))}`;
    case 'percent':
      return `${n.toFixed(n < 10 && n % 1 !== 0 ? 1 : 0)}%`;
    case 'duration':
      return duration(n);
    case 'multiple':
      return `${n.toFixed(2)}×`;
    case 'integer':
      return int(Math.round(n));
    case 'date':
      return dateShort(n);
    case 'boolean':
      return value ? 'Yes' : 'No';
    case 'enum':
      return def.options?.find((o) => o.value === value)?.label ?? String(value);
    default:
      return String(value);
  }
}

export function operatorLabel(def: CheckDefinition, op: CheckOperator): string {
  return (def.valueType === 'date' ? DATE_OPERATOR_LABEL[op] : undefined) ?? OPERATOR_LABEL[op];
}

/** The unit that trails a number inside the chip. Derived from the value
 *  type rather than stored, so no definition can disagree with its type. */
export function valueSuffix(def: CheckDefinition): string | null {
  if (def.valueType === 'percent') return '%';
  if (def.valueType === 'multiple') return '×';
  return null;
}

/** Duration inputs are stored in minutes but typed in whatever unit suits
 *  the magnitude — nobody wants to enter 43,200 to mean a month. */
export const DURATION_UNITS = [
  { id: 'min', label: 'min', factor: 1 },
  { id: 'hr', label: 'hr', factor: 60 },
  { id: 'day', label: 'day', factor: 60 * 24 },
] as const;

export function bestDurationUnit(minutes: number) {
  const m = Math.abs(minutes);
  if (m >= 60 * 24 && m % (60 * 24) === 0) return DURATION_UNITS[2];
  if (m >= 60 && m % 60 === 0) return DURATION_UNITS[1];
  return DURATION_UNITS[0];
}
