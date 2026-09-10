import { useEffect, useState } from 'react';
import type { AppliedCheck, CheckDefinition, CheckValue } from '../../data/types';
import {
  DURATION_UNITS,
  bestDurationUnit,
  operatorLabel,
  valueSuffix,
} from '../../lib/check-format';
import { dateInput } from '../../lib/format';

/* ============================================================
   A filter is a chip. Off, it is only its name. Click it and it turns to
   ink and opens its own value in place — operator, number, unit — so the
   thing being set and the setting are one object, not a label in one
   place and a form somewhere else.
   ============================================================ */

/** Hollow ring = derived: needs clustering, labelling or price history a
 *  real deployment would supply. Direct checks carry no mark, because
 *  direct is the normal case and marking the normal case is noise. */
export function DerivedRing() {
  return (
    <span
      className="bl-ring"
      title="Derived — needs clustering, labelling or price history this build does not run"
      aria-label="derived"
    />
  );
}

/** A number field that keeps what the user is typing — including an empty
 *  box mid-edit — and only reports values that parse. A bare controlled
 *  number input snaps "" back to 0, which makes it impossible to retype. */
function NumberField({
  value,
  onCommit,
  label,
}: {
  value: number;
  onCommit: (n: number) => void;
  label: string;
}) {
  const [text, setText] = useState(String(value));

  /* follow outside changes (a preset, a unit switch) without fighting typing */
  useEffect(() => {
    if (Number(text) !== value) setText(String(Number(value.toFixed(4))));
  }, [value]);

  return (
    <input
      className="bl-chip__num num"
      inputMode="decimal"
      value={text}
      aria-label={label}
      style={{ width: `${Math.max(2, text.length) + 1}ch` }}
      onChange={(e) => {
        const v = e.target.value.replace(/[^0-9.\-]/g, '');
        setText(v);
        const n = Number(v);
        if (v.trim() !== '' && v !== '-' && Number.isFinite(n)) onCommit(n);
      }}
    />
  );
}

function Editor({
  def,
  check,
  onChange,
}: {
  def: CheckDefinition;
  check: AppliedCheck;
  onChange: (next: AppliedCheck) => void;
}) {
  const set = (value: CheckValue) => onChange({ ...check, value });
  /* the unit is a view concern; the stored value is always minutes */
  const [unit, setUnit] = useState(() => bestDurationUnit(Number(check.value)));

  const op =
    def.valueType === 'boolean' ? null : def.operators.length > 1 ? (
      <button
        type="button"
        className="bl-chip__op"
        title="Change comparison"
        onClick={() => {
          const i = def.operators.indexOf(check.operator);
          onChange({ ...check, operator: def.operators[(i + 1) % def.operators.length] });
        }}
      >
        {operatorLabel(def, check.operator)}
      </button>
    ) : (
      <span className="bl-chip__op bl-chip__op--fixed">{operatorLabel(def, check.operator)}</span>
    );

  let field: React.ReactNode;
  switch (def.valueType) {
    case 'boolean':
      field = (
        <button type="button" className="bl-chip__bool" onClick={() => set(!check.value)}>
          {check.value ? 'Yes' : 'No'}
        </button>
      );
      break;

    case 'enum':
      field = (
        <select
          className="bl-chip__sel"
          value={String(check.value)}
          onChange={(e) => set(e.target.value)}
          aria-label={`${def.label} value`}
        >
          {def.options?.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      );
      break;

    case 'date':
      field = (
        <input
          type="date"
          className="bl-chip__date num"
          value={dateInput(Number(check.value))}
          aria-label={`${def.label} date`}
          onChange={(e) => {
            const ms = Date.parse(`${e.target.value}T00:00:00Z`);
            if (!Number.isNaN(ms)) set(ms);
          }}
        />
      );
      break;

    case 'duration': {
      field = (
        <>
          <NumberField
            value={Number(check.value) / unit.factor}
            onCommit={(n) => set(n * unit.factor)}
            label={`${def.label} value`}
          />
          <select
            className="bl-chip__sel bl-chip__sel--unit"
            value={unit.id}
            aria-label="unit"
            onChange={(e) => {
              const next = DURATION_UNITS.find((u) => u.id === e.target.value)!;
              /* keep the number on screen, change what it means */
              set((Number(check.value) / unit.factor) * next.factor);
              setUnit(next);
            }}
          >
            {DURATION_UNITS.map((u) => (
              <option key={u.id} value={u.id}>
                {u.label}
              </option>
            ))}
          </select>
        </>
      );
      break;
    }

    default: {
      const suffix = valueSuffix(def);
      field = (
        <>
          {def.valueType === 'currency' && <span className="bl-chip__affix num">$</span>}
          <NumberField value={Number(check.value)} onCommit={set} label={`${def.label} value`} />
          {suffix && <span className="bl-chip__affix num">{suffix}</span>}
        </>
      );
    }
  }

  return (
    <span className="bl-chip__edit">
      {op}
      {field}
    </span>
  );
}

export function FilterChip({
  def,
  applied,
  onToggle,
  onChange,
}: {
  def: CheckDefinition;
  /** undefined while the filter is off */
  applied?: AppliedCheck;
  onToggle: () => void;
  onChange: (next: AppliedCheck) => void;
}) {
  const on = applied !== undefined;

  return (
    <span className="bl-chip" data-on={on}>
      <button type="button" className="bl-chip__l" onClick={onToggle} aria-pressed={on}>
        {def.derivation === 'derived' && <DerivedRing />}
        {def.label}
      </button>
      {on && <Editor def={def} check={applied} onChange={onChange} />}
      {on && (
        <button
          type="button"
          className="bl-chip__x"
          onClick={onToggle}
          aria-label={`Turn off ${def.label}`}
        >
          <svg viewBox="0 0 20 20" width="10" height="10" aria-hidden="true">
            <path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="2" fill="none" />
          </svg>
        </button>
      )}
    </span>
  );
}
